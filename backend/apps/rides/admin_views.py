from rest_framework.views import APIView
from rest_framework.response import Response
from apps.users.permissions import IsAdmin
from apps.rides.models import Ride
from django.utils import timezone
from decimal import Decimal
from django.db import transaction

class AdminRidesListView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        rides = Ride.objects.select_related("rider", "driver__user").order_by("-created_at")[:50]
        data = []
        for r in rides:
            from apps.payments.models import Payment
            payment = Payment.objects.filter(ride_id=r.id, status=Payment.Status.CAPTURED).first()
            data.append({
                "id": r.id,
                "rider_phone": r.rider.phone,
                "rider_name": r.rider.get_full_name() or r.rider.username,
                "driver_phone": r.driver.user.phone if r.driver else None,
                "status": r.status,
                "payment_status": payment.status if payment else None,
                "base_fare": str(r.base_fare),
                "final_fare": str(r.final_fare) if r.final_fare else None,
                "created_at": r.created_at,
            })
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
            return Response({"error": "ride_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        if action not in ["cancel", "reassign", "refund", "compensate_driver"]:
            return Response({"error": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            ride = Ride.objects.get(id=ride_id)
            
            if action == "cancel":
                # Option: refund_amount (Decimal), compensate_driver_amount (Decimal)
                refund_amount = Decimal(str(request.data.get("refund_amount", 0)))
                comp_amount = Decimal(str(request.data.get("compensate_driver_amount", 0)))

                with transaction.atomic():
                    # 1. Cancel Ride
                    service_cancel_ride(ride=ride, by=Ride.CancelledBy.ADMIN)
                    
                    # 2. Refund Rider if requested
                    if refund_amount > 0:
                        from apps.payments.models import Payment
                        from apps.payments.services.refund import refund_payment
                        payment = Payment.objects.filter(ride_id=ride.id, status=Payment.Status.CAPTURED).first()
                        if payment:
                            # Clamp amount to not exceed payment total
                            actual_refund = min(refund_amount, payment.amount)
                            refund_payment(
                                payment=payment,
                                amount=actual_refund,
                                reason="Admin cancellation: Manual refund",
                                initiated_by=request.user
                            )

                    # 3. Compensate Driver if requested
                    if comp_amount > 0 and ride.driver:
                        from apps.payments.services.compensation import compensate_driver
                        compensate_driver(
                            driver=ride.driver,
                            ride_id=ride.id,
                            amount=comp_amount,
                            reason="Admin cancellation: Driver compensation"
                        )

                logger.info(f"Ride {ride_id} cancelled by admin {request.user.id} with refund={refund_amount}, comp={comp_amount}")
            
            elif action == "compensate_driver":
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
                    reason=request.data.get("reason", "Admin manual adjustment")
                )
                logger.info(f"Admin {request.user.id} compensated Driver {ride.driver_id} for Ride {ride_id}: {amount}")

            elif action == "reassign":
                # Only allow reassigning if the ride is in a state that has a driver assigned
                if ride.status not in [Ride.Status.ASSIGNED, Ride.Status.ARRIVED, Ride.Status.OFFERED]:
                    return Response({"error": "Ride is not in a reassignable state"}, status=400)
                
                old_driver = ride.driver
                ride.driver = None
                ride.status = Ride.Status.SEARCHING
                ride.candidate_driver_ids = [] # Clear so it searches fresh
                ride.rejected_driver_ids = []  # Clear so old rejections don't block
                ride.save()
                
                # If there was an old driver, free them up
                if old_driver:
                    old_driver.status = "ONLINE"
                    old_driver.save(update_fields=["status"])
                
                logger.info(f"Ride {ride_id} reassigned by admin {request.user.id}")

            elif action == "refund":
                from apps.payments.models import Payment
                from apps.payments.services.refund import refund_payment
                
                payment = Payment.objects.filter(ride_id=ride.id, status=Payment.Status.CAPTURED).first()
                if not payment:
                    return Response({"error": "No captured payment found for this ride"}, status=400)
                
                refund_payment(
                    payment=payment,
                    amount=payment.amount,
                    reason="Admin manual refund",
                    initiated_by=request.user
                )
                logger.info(f"Payment for Ride {ride_id} successfully refunded via Razorpay by admin {request.user.id}")

            return Response({"success": True, "status": ride.status})

        except Ride.DoesNotExist:
             logger.warning(f"Admin tried to action non-existent ride {ride_id}")
             return Response({"error": "Ride not found"}, status=status.HTTP_404_NOT_FOUND)
             
        except Exception as e:
            logger.error(f"Failed to action ride {ride_id} via admin: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class ResolveRideView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request):
        ride_id = request.data.get("ride_id")
        action = request.data.get("action")
        reason = request.data.get("reason", "No reason provided")
        
        # Guard against invalid decimal inputs (NaN, empty, etc)
        def clean_decimal(val):
            try:
                if val is None or val == "" or str(val).lower() == "nan":
                    return Decimal("0.00")
                return Decimal(str(val))
            except:
                return Decimal("0.00")

        refund_amount = clean_decimal(request.data.get("refund_amount", 0))
        comp_amount = clean_decimal(request.data.get("driver_compensation", 0))
        penalty_amount = clean_decimal(request.data.get("penalty_amount", 0))
        waive_fee = request.data.get("waive_fee", False)

        if not ride_id:
            return Response({"error": "ride_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                ride = Ride.objects.select_for_update().get(id=ride_id)
                driver = ride.driver

                # 1. Action (Optional Cancellation)
                if action == "CANCEL" and ride.status not in [Ride.Status.COMPLETED, Ride.Status.CANCELLED]:
                    service_cancel_ride(ride=ride, by=Ride.CancelledBy.ADMIN)
                    # Note: service_cancel_ride handles notifications and driver release
                
                # 2. Refund Rider
                if refund_amount > 0:
                    from apps.payments.models import Payment, LedgerEntry
                    from apps.payments.services.refund import refund_payment
                    payment = Payment.objects.filter(ride_id=ride.id, status=Payment.Status.CAPTURED).first()
                    if payment:
                        actual_refund = min(refund_amount, payment.amount)
                        refund_payment(
                            payment=payment,
                            amount=actual_refund,
                            reason=LedgerEntry.Reason.REFUND,
                            initiated_by=request.user
                        )
                    else:
                        # Fallback: Issue as manual credit (Compensation) if no payment to refund
                        LedgerEntry.objects.create(
                            user=ride.rider,
                            ride_id=ride.id,
                            amount=refund_amount,
                            entry_type=LedgerEntry.Type.CREDIT,
                            reason=LedgerEntry.Reason.REFUND,
                            reference=f"manual_credit:{ride.id}"
                        )

                # 3. Driver Compensation
                if comp_amount > 0 and driver:
                    from apps.payments.services.compensation import compensate_driver
                    compensate_driver(
                        driver=driver,
                        ride_id=ride.id,
                        amount=comp_amount,
                        reason=f"Admin Resolution: {reason}"
                    )

                # 4. Driver Penalty
                if penalty_amount > 0 and driver:
                    from apps.payments.models import LedgerEntry
                    import uuid
                    LedgerEntry.objects.create(
                        user=driver.user,
                        ride_id=ride.id,
                        amount=penalty_amount,
                        entry_type=LedgerEntry.Type.DEBIT,
                        reason=LedgerEntry.Reason.PENALTY,
                        reference=f"penalty:{ride.id}_{uuid.uuid4().hex[:8]}"
                    )
                    # Notify Driver
                    from apps.notifications.models import Notification
                    Notification.objects.create(
                        user=driver.user,
                        channel="push",
                        type="PENALTY_APPLIED",
                        payload={"ride_id": ride.id, "amount": float(penalty_amount), "message": f"A penalty of ₹{penalty_amount} has been applied to your account. Reason: {reason}"}
                    )
                
                # 5. Automated Rating/Penalty Rules
                if driver:
                    stats = getattr(driver, 'stats', None)
                    if stats:
                        if reason == "Driver not moving":
                            # Rule: Deduct more if driver failed to move
                            penalty_auto = Decimal("50.00")
                            LedgerEntry.objects.create(
                                user=driver.user,
                                ride_id=ride.id,
                                amount=penalty_auto,
                                entry_type=LedgerEntry.Type.DEBIT,
                                reason=LedgerEntry.Reason.PENALTY,
                                reference=f"auto_penalty_no_move:{ride.id}_{uuid.uuid4().hex[:8]}"
                            )
                            # Notify Driver
                            from apps.notifications.models import Notification
                            Notification.objects.create(
                                user=driver.user,
                                channel="push",
                                type="PENALTY_APPLIED",
                                payload={"ride_id": ride.id, "amount": 50.0, "message": "An automatic penalty of ₹50 has been applied: Driver not moving."}
                            )
                        
                        if "Bad experience" in reason:
                            # Rule: Reduce rating
                            stats.avg_rating = max(1.0, stats.avg_rating - 0.2)
                            stats.save(update_fields=["avg_rating"])

                # 6. Waive Platform Fee (if requested and payment captured)
                if waive_fee:
                    from apps.payments.models import Payment, LedgerEntry
                    payment = Payment.objects.filter(ride_id=ride.id, status=Payment.Status.CAPTURED).first()
                    if payment:
                        # Find the existing commission entry to reverse it
                        platform_comm = LedgerEntry.objects.filter(
                            ride_id=ride.id,
                            reason=LedgerEntry.Reason.PLATFORM_COMMISSION
                        ).first()
                        
                        if platform_comm:
                            # Debit platform, Credit driver
                            from apps.payments.services.payout import _platform_user
                            platform = _platform_user()
                            
                            # 1. Reverse platform credit
                            LedgerEntry.objects.create(
                                user=platform,
                                ride_id=ride.id,
                                amount=platform_comm.amount,
                                entry_type=LedgerEntry.Type.DEBIT,
                                reason=LedgerEntry.Reason.PLATFORM_COMMISSION,
                                reference=f"waive_comm_rev:{ride.id}"
                            )
                            
                            # 2. Credit driver with the waived amount
                            if driver:
                                LedgerEntry.objects.create(
                                    user=driver.user,
                                    ride_id=ride.id,
                                    amount=platform_comm.amount,
                                    entry_type=LedgerEntry.Type.CREDIT,
                                    reason=LedgerEntry.Reason.OTHER,
                                    reference=f"waive_comm_bonus:{ride.id}"
                                )

                # Audit Log (Simplified using Python Logging - in prod use a dedicated Audit model)
                logger.info(f"RIDE_RESOLUTION: Admin={request.user.id} Ride={ride.id} Action={action} Reason={reason} Refund={refund_amount} Comp={comp_amount} Penalty={penalty_amount} Waived={waive_fee}")

            return Response({"success": True, "message": "Ride resolved and audited."})

        except Ride.DoesNotExist:
            return Response({"error": "Ride not found"}, status=404)
        except Exception as e:
            logger.error(f"Resolution failed: {str(e)}")
            return Response({"error": str(e)}, status=500)
