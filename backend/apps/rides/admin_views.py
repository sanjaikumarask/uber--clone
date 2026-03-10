from decimal import Decimal

from django.db import transaction
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.rides.models import Ride
from apps.users.permissions import IsAdmin


class AdminRidesListView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        rides = Ride.objects.select_related("rider", "driver__user").order_by(
            "-created_at"
        )[:50]
        data = []
        for r in rides:
            from apps.payments.models import Payment

            payment = Payment.objects.filter(
                ride_id=r.id, status=Payment.Status.CAPTURED
            ).first()
            data.append(
                {
                    "id": r.id,
                    "rider_phone": r.rider.phone,
                    "rider_name": r.rider.get_full_name() or r.rider.username,
                    "driver_phone": r.driver.user.phone if r.driver else None,
                    "status": r.status,
                    "payment_status": payment.status if payment else None,
                    "base_fare": str(r.base_fare),
                    "final_fare": str(r.final_fare) if r.final_fare else None,
                    "created_at": r.created_at,
                }
            )
        return Response(data)


import logging

from rest_framework import status

from apps.rides.services.cancellation import cancel_ride as service_cancel_ride

logger = logging.getLogger(__name__)


class AdminRideActionView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request):
        ride_id = request.data.get("ride_id")
        action = request.data.get("action")

        logger.info(f"Admin action triggered: {action} on ride {ride_id}")

        if not ride_id:
            return Response(
                {"error": "ride_id is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        if action not in ["cancel", "reassign", "refund", "compensate_driver"]:
            return Response(
                {"error": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            ride = Ride.objects.get(id=ride_id)
            return self._handle_action(request, ride, action)

        except Ride.DoesNotExist:
            logger.warning(f"Admin tried to action non-existent ride {ride_id}")
            return Response(
                {"error": "Ride not found"}, status=status.HTTP_404_NOT_FOUND
            )

        except Exception as e:
            logger.error(f"Failed to action ride {ride_id} via admin: {e!s}")
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def _handle_action(self, request, ride, action):
        if action == "cancel":
            return self._handle_cancel(request, ride)
        elif action == "compensate_driver":
            return self._handle_compensate(request, ride)
        elif action == "reassign":
            return self._handle_reassign(request, ride)
        elif action == "refund":
            return self._handle_refund(request, ride)
        return Response({"success": True, "status": ride.status})

    def _handle_cancel(self, request, ride):
        refund_amount = Decimal(str(request.data.get("refund_amount", 0)))
        comp_amount = Decimal(str(request.data.get("compensate_driver_amount", 0)))

        with transaction.atomic():
            service_cancel_ride(ride=ride, by=Ride.CancelledBy.ADMIN)
            self._apply_cancel_monetary_actions(ride, refund_amount, comp_amount)

        logger.info(
            f"Ride {ride.id} cancelled by admin {request.user.id} with refund={refund_amount}, comp={comp_amount}"
        )
        return Response({"success": True, "status": ride.status})

    def _apply_cancel_monetary_actions(self, ride, refund_amount, comp_amount):
        if refund_amount > 0:
            from apps.payments.models import Payment
            from apps.payments.services.refund import refund_payment
            payment = Payment.objects.filter(ride_id=ride.id, status=Payment.Status.CAPTURED).first()
            if payment:
                actual_refund = min(refund_amount, payment.amount)
                refund_payment(payment=payment, amount=actual_refund, reason="Admin cancellation: Manual refund")

        if comp_amount > 0 and ride.driver:
            from apps.payments.services.compensation import compensate_driver
            compensate_driver(driver=ride.driver, ride_id=ride.id, amount=comp_amount, reason="Admin cancellation: Driver compensation")

    def _handle_compensate(self, request, ride):
        amount = Decimal(str(request.data.get("amount", 0)))
        if amount <= 0:
            return Response({"error": "Amount required"}, status=400)
        if not ride.driver:
            return Response({"error": "No driver assigned to this ride"}, status=400)

        from apps.payments.services.compensation import compensate_driver
        compensate_driver(
            driver=ride.driver,
            ride_id=ride.id,
            amount=amount,
            reason=request.data.get("reason", "Admin manual adjustment"),
        )
        logger.info(f"Admin {request.user.id} compensated Driver {ride.driver_id} for Ride {ride.id}: {amount}")
        return Response({"success": True, "status": ride.status})

    def _handle_reassign(self, request, ride):
        if ride.status not in [Ride.Status.ASSIGNED, Ride.Status.ARRIVED, Ride.Status.OFFERED]:
            return Response({"error": "Ride is not in a reassignable state"}, status=400)

        old_driver = ride.driver
        ride.driver = None
        ride.status = Ride.Status.SEARCHING
        ride.candidate_driver_ids = []
        ride.rejected_driver_ids = []
        ride.save()

        if old_driver:
            old_driver.status = "ONLINE"
            old_driver.save(update_fields=["status"])

        logger.info(f"Ride {ride.id} reassigned by admin {request.user.id}")
        return Response({"success": True, "status": ride.status})

    def _handle_refund(self, request, ride):
        from apps.payments.models import Payment
        from apps.payments.services.refund import refund_payment

        payment = Payment.objects.filter(ride_id=ride.id, status=Payment.Status.CAPTURED).first()
        if not payment:
            return Response({"error": "No captured payment found for this ride"}, status=400)

        refund_payment(payment=payment, amount=payment.amount, reason="Admin manual refund")
        logger.info(f"Payment for Ride {ride.id} successfully refunded via Razorpay by admin {request.user.id}")
        return Response({"success": True, "status": ride.status})


class ResolveRideView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request):
        ride_id = request.data.get("ride_id")
        action = request.data.get("action")
        reason = request.data.get("reason", "No reason provided")

        if not ride_id:
            return Response({"error": "ride_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        params = self._get_resolution_params(request)

        try:
            with transaction.atomic():
                ride = Ride.objects.select_for_update().get(id=ride_id)
                self._apply_resolution(request, ride, action, reason, params)

            return Response({"success": True, "message": "Ride resolved and audited."})

        except Ride.DoesNotExist:
            return Response({"error": "Ride not found"}, status=404)
        except Exception as e:
            logger.error(f"Resolution failed: {e!s}")
            return Response({"error": str(e)}, status=500)

    def _get_resolution_params(self, request):
        from decimal import InvalidOperation

        def clean_decimal(val):
            try:
                if val is None or val == "" or str(val).lower() == "nan":
                    return Decimal("0.00")
                return Decimal(str(val))
            except (TypeError, ValueError, InvalidOperation):
                return Decimal("0.00")

        return {
            "refund_amount": clean_decimal(request.data.get("refund_amount", 0)),
            "comp_amount": clean_decimal(request.data.get("driver_compensation", 0)),
            "penalty_amount": clean_decimal(request.data.get("penalty_amount", 0)),
            "waive_fee": request.data.get("waive_fee", False),
        }

    def _apply_resolution(self, request, ride, action, reason, params):
        driver = ride.driver

        if action == "CANCEL" and ride.status not in [Ride.Status.COMPLETED, Ride.Status.CANCELLED]:
            service_cancel_ride(ride=ride, by=Ride.CancelledBy.ADMIN)

        if params["refund_amount"] > 0:
            self._refund_rider(ride, params["refund_amount"])

        if params["comp_amount"] > 0 and driver:
            from apps.payments.services.compensation import compensate_driver
            compensate_driver(driver=driver, ride_id=ride.id, amount=params["comp_amount"], reason=f"Admin Resolution: {reason}")

        if params["penalty_amount"] > 0 and driver:
            self._apply_driver_penalty(ride, driver, params["penalty_amount"], reason)

        if driver:
            self._handle_automated_rules(ride, driver, reason)

        if params["waive_fee"]:
            self._waive_platform_fee(ride, driver)

        logger.info(
            f"RIDE_RESOLUTION: Admin={request.user.id} Ride={ride.id} Action={action} Reason={reason} "
            f"Refund={params['refund_amount']} Comp={params['comp_amount']} Penalty={params['penalty_amount']} Waived={params['waive_fee']}"
        )

    def _refund_rider(self, ride, amount):
        from apps.payments.models import LedgerEntry, Payment
        from apps.payments.services.refund import refund_payment

        payment = Payment.objects.filter(ride_id=ride.id, status=Payment.Status.CAPTURED).first()
        if payment:
            actual_refund = min(amount, payment.amount)
            refund_payment(payment=payment, amount=actual_refund, reason=LedgerEntry.Reason.REFUND)
        else:
            LedgerEntry.objects.create(
                user=ride.rider,
                ride_id=ride.id,
                amount=amount,
                entry_type=LedgerEntry.Type.CREDIT,
                reason=LedgerEntry.Reason.REFUND,
                reference=f"manual_credit:{ride.id}",
            )

    def _apply_driver_penalty(self, ride, driver, amount, reason):
        import uuid
        from apps.payments.models import LedgerEntry
        from apps.notifications.models import Notification

        LedgerEntry.objects.create(
            user=driver.user,
            ride_id=ride.id,
            amount=amount,
            entry_type=LedgerEntry.Type.DEBIT,
            reason=LedgerEntry.Reason.PENALTY,
            reference=f"penalty:{ride.id}_{uuid.uuid4().hex[:8]}",
        )
        Notification.objects.create(
            user=driver.user,
            channel="push",
            type="PENALTY_APPLIED",
            payload={
                "ride_id": ride.id,
                "amount": float(amount),
                "message": f"A penalty of ₹{amount} has been applied to your account. Reason: {reason}",
            },
        )

    def _handle_automated_rules(self, ride, driver, reason):
        import uuid
        from apps.payments.models import LedgerEntry
        from apps.notifications.models import Notification

        stats = getattr(driver, "stats", None)
        if stats:
            if reason == "Driver not moving":
                penalty_auto = Decimal("50.00")
                LedgerEntry.objects.create(
                    user=driver.user,
                    ride_id=ride.id,
                    amount=penalty_auto,
                    entry_type=LedgerEntry.Type.DEBIT,
                    reason=LedgerEntry.Reason.PENALTY,
                    reference=f"auto_penalty_no_move:{ride.id}_{uuid.uuid4().hex[:8]}",
                )
                Notification.objects.create(
                    user=driver.user,
                    channel="push",
                    type="PENALTY_APPLIED",
                    payload={
                        "ride_id": ride.id,
                        "amount": 50.0,
                        "message": "An automatic penalty of ₹50 has been applied: Driver not moving.",
                    },
                )
            if "Bad experience" in reason:
                stats.avg_rating = max(1.0, stats.avg_rating - 0.2)
                stats.save(update_fields=["avg_rating"])

    def _waive_platform_fee(self, ride, driver):
        from apps.payments.models import LedgerEntry, Payment
        payment = Payment.objects.filter(ride_id=ride.id, status=Payment.Status.CAPTURED).first()
        if payment:
            platform_comm = LedgerEntry.objects.filter(
                ride_id=ride.id,
                reason=LedgerEntry.Reason.PLATFORM_COMMISSION,
            ).first()

            if platform_comm:
                from apps.payments.services.payout import _platform_user
                platform = _platform_user()
                LedgerEntry.objects.create(
                    user=platform,
                    ride_id=ride.id,
                    amount=platform_comm.amount,
                    entry_type=LedgerEntry.Type.DEBIT,
                    reason=LedgerEntry.Reason.PLATFORM_COMMISSION,
                    reference=f"waive_comm_rev:{ride.id}",
                )
                if driver:
                    LedgerEntry.objects.create(
                        user=driver.user,
                        ride_id=ride.id,
                        amount=platform_comm.amount,
                        entry_type=LedgerEntry.Type.CREDIT,
                        reason=LedgerEntry.Reason.OTHER,
                        reference=f"waive_comm_bonus:{ride.id}",
                    )
