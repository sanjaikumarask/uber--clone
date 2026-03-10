import logging

from django.db import transaction

logger = logging.getLogger(__name__)
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.idempotency import idempotent_request
from apps.payments.models import Payment
from apps.payments.services.payout import settle_driver_payout
from apps.rides.models import Ride

from .models import LedgerEntry
from .razorpay_client import razorpay_client


class SimulatedPaymentView(APIView):
    """
    Simulates a successful payment for testing when Razorpay
    is not fully configured.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, ride_id):
        logger.info(
            f"SIMULATE_PAYMENT: User {request.user.id} requesting for Ride {ride_id}"
        )

        with transaction.atomic():
            try:
                ride = Ride.objects.select_for_update().get(id=ride_id)
            except Ride.DoesNotExist:
                return Response(
                    {"error": "Ride not found"}, status=status.HTTP_404_NOT_FOUND
                )

            if ride.rider != request.user and not request.user.is_admin:
                logger.warning(
                    f"SIMULATE_PAYMENT: Permission Denied. Ride rider is {ride.rider_id}, but caller is {request.user.id}"
                )
                return Response(
                    {"error": "You do not have permission to pay for this ride"},
                    status=status.HTTP_403_FORBIDDEN,
                )

            if ride.status != Ride.Status.COMPLETED:
                return Response(
                    {
                        "error": f"Ride is in {ride.status} state, cannot process payment"
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Check if already paid
            if Payment.objects.filter(
                ride_id=ride.id, status=Payment.Status.CAPTURED
            ).exists():
                return Response({"status": "already_paid"})

            # Try to find existing CREATED payment (made by ride completion lifecycle)
            payment = Payment.objects.filter(
                ride_id=ride.id, status=Payment.Status.CREATED
            ).first()

            if payment:
                payment.status = Payment.Status.CAPTURED
                payment.gateway = "simulation"
                payment.gateway_payment_id = f"sim_{ride.id}_{request.user.id}"
                payment.save(update_fields=["status", "gateway", "gateway_payment_id"])
            else:
                payment = Payment.objects.create(
                    user=request.user,
                    ride_id=ride.id,
                    amount=ride.final_fare,
                    status=Payment.Status.CAPTURED,
                    gateway="simulation",
                    gateway_payment_id=f"sim_{ride.id}_{request.user.id}",
                )

            # Record ledger
            LedgerEntry.objects.create(
                user=payment.user,
                ride_id=payment.ride_id,
                amount=payment.amount,
                entry_type=LedgerEntry.Type.DEBIT,
                reason=LedgerEntry.Reason.PAYMENT,
                reference=payment.gateway_payment_id,
            )

            # 2️⃣ Platform → Driver payout + commission split
            settle_driver_payout(
                ride=ride,
                payment=payment,
            )

            # Notify Rider of successful payment (Simulated)
            from apps.notifications.models import Notification

            transaction.on_commit(
                lambda: Notification.objects.create(
                    user=request.user,
                    channel="email",
                    type="PAYMENT_CONFIRMED",
                    payload={
                        "subject": f"Payment Successful (Simulated) - Ride #{ride.id}",
                        "body": f"Hi {request.user.first_name}, your test payment of ₹{ride.final_fare} was successful.",
                        "html": f"<h2>Test Payment Successful ✅</h2><p>Your simulated payment of <strong>₹{ride.final_fare}</strong> for ride #{ride.id} was processed successfully.</p>",
                    },
                )
            )

        return Response(
            {
                "status": "success",
                "payment_id": payment.id,
                "amount": float(payment.amount),
            }
        )


class CreatePaymentOrderView(APIView):
    permission_classes = [IsAuthenticated]

    @idempotent_request(ttl=300)
    def post(self, request, ride_id):
        logger.info(
            f"CREATE_PAYMENT: User {request.user.id} ({request.user.username}) requesting for Ride {ride_id}"
        )

        try:
            ride = Ride.objects.get(id=ride_id)
        except Ride.DoesNotExist:
            return Response(
                {"error": "Ride record not found"}, status=status.HTTP_404_NOT_FOUND
            )

        if ride.rider != request.user and not request.user.is_admin:
            logger.warning(
                f"CREATE_PAYMENT: Permission Denied. Ride rider is {ride.rider_id}, but caller is {request.user.id}"
            )
            return Response(
                {
                    "error": "Access denied. You are not the registered rider for this trip."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if ride.status != Ride.Status.COMPLETED:
            return Response(
                {
                    "error": f"Ride is in '{ride.status}' state. Payment can only be initiated for completed rides."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if ride.final_fare is None or ride.final_fare <= 0:
            return Response(
                {
                    "error": "Trip fare has not been finalized yet. Please try again in a moment."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not razorpay_client:
            return Response(
                {
                    "error": "Payment gateway not configured. Use simulation mode or contact support."
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        with transaction.atomic():
            # Re-fetch with lock inside the transaction
            ride = Ride.objects.select_for_update().get(id=ride_id)

            # Reuse existing CREATED payment if lifecycle already made one
            payment = Payment.objects.filter(
                ride_id=ride.id, status=Payment.Status.CREATED
            ).first()

            # ✅ IDEMPOTENCY: Check if already paid
            if Payment.objects.filter(
                ride_id=ride.id, status=Payment.Status.CAPTURED
            ).exists():
                return Response(
                    {"error": "Payment has already been captured for this ride."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if not payment:
                payment = Payment.objects.create(
                    user=request.user,
                    ride_id=ride.id,
                    amount=ride.final_fare,
                    status=Payment.Status.CREATED,
                )

            try:
                order = razorpay_client.order.create(
                    {
                        "amount": int(ride.final_fare * 100),  # paise
                        "currency": "INR",
                        "receipt": f"ride_{ride.id}_payment_{payment.id}",
                        "payment_capture": 1,
                    }
                )
            except Exception as e:
                logger.error(f"Razorpay order creation failed: {e}")
                error_msg = str(e)
                if "Authentication failed" in error_msg:
                    error_msg = "Gateway authentication failure. Please check server configuration."
                return Response(
                    {"error": error_msg},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            payment.gateway_order_id = order["id"]
            payment.save(update_fields=["gateway_order_id"])

        return Response(
            {
                "payment_id": payment.id,
                "order_id": order["id"],
                "amount": order["amount"],
                "currency": order["currency"],
                "key": razorpay_client.auth[0],
            }
        )


class VerifyPaymentView(APIView):
    permission_classes = [IsAuthenticated]

    @idempotent_request(ttl=300)
    def post(self, request):
        if not razorpay_client:
            return Response(
                {"error": "Payment gateway not configured"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        data = request.data

        required = {
            "razorpay_order_id",
            "razorpay_payment_id",
            "razorpay_signature",
        }

        if not required.issubset(data):
            return Response(
                {"error": "Invalid payload"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 🔐 Verify Razorpay signature
        try:
            razorpay_client.utility.verify_payment_signature(
                {
                    "razorpay_order_id": data["razorpay_order_id"],
                    "razorpay_payment_id": data["razorpay_payment_id"],
                    "razorpay_signature": data["razorpay_signature"],
                }
            )
        except Exception:
            return Response(
                {"error": "Signature verification failed"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            try:
                payment = Payment.objects.select_for_update().get(
                    gateway_order_id=data["razorpay_order_id"]
                )
            except Payment.DoesNotExist:
                return Response(
                    {"error": "Payment record not found for this order"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Security: Ensure this payment belongs to the caller (allow admins)
            if payment.user != request.user and not request.user.is_admin:
                logger.warning(
                    f"VERIFY_PAYMENT: Permission Denied. Payment user is {payment.user_id}, but caller is {request.user.id}"
                )
                return Response(
                    {"error": "Unauthorized signature verification"},
                    status=status.HTTP_403_FORBIDDEN,
                )

            # ✅ Idempotent protection
            if payment.status == Payment.Status.CAPTURED:
                return Response({"status": "already_captured"})

            payment.gateway_payment_id = data["razorpay_payment_id"]
            payment.gateway_signature = data["razorpay_signature"]
            payment.status = Payment.Status.CAPTURED
            payment.save()

            # 1️⃣ Rider pays platform
            LedgerEntry.objects.create(
                user=payment.user,
                ride_id=payment.ride_id,
                amount=payment.amount,
                entry_type=LedgerEntry.Type.DEBIT,
                reason=LedgerEntry.Reason.PAYMENT,
                reference=f"payment:{payment.gateway_payment_id}",
            )

            # 2️⃣ Platform → Driver payout + commission split
            ride = Ride.objects.select_for_update().get(id=payment.ride_id)
            settle_driver_payout(
                ride=ride,
                payment=payment,
            )

            # 3️⃣ Notify Rider of successful payment
            from apps.notifications.models import Notification

            transaction.on_commit(
                lambda: Notification.objects.create(
                    user=payment.user,
                    channel="email",
                    type="PAYMENT_CONFIRMED",
                    payload={
                        "subject": f"Payment Successful - Ride #{payment.ride_id}",
                        "body": f"Hi {payment.user.first_name}, your payment of ₹{payment.amount} was successful. Trans ID: {payment.gateway_payment_id}",
                        "html": f"<h2>Payment Successful ✅</h2><p>Your payment of <strong>₹{payment.amount}</strong> has been received for ride #{payment.ride_id}.</p><p>Transaction ID: {payment.gateway_payment_id}</p>",
                    },
                )
            )

        return Response({"status": "success"})
