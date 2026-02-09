from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from apps.payments.models import Payment, LedgerEntry
from apps.payments.services.payout import settle_driver_payout
from apps.rides.models import Ride
from .razorpay_client import razorpay_client


class CreatePaymentOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, ride_id):
        ride = get_object_or_404(
            Ride,
            id=ride_id,
            rider=request.user,
            status=Ride.Status.COMPLETED,
        )

        if ride.final_fare is None or ride.final_fare <= 0:
            return Response(
                {"error": "Final fare not locked"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            payment = Payment.objects.create(
                user=request.user,
                ride_id=ride.id,
                amount=ride.final_fare,
            )

            order = razorpay_client.order.create({
                "amount": int(ride.final_fare * 100),  # paise
                "currency": "INR",
                "receipt": f"ride_{ride.id}_payment_{payment.id}",
                "payment_capture": 1,
            })

            payment.gateway_order_id = order["id"]
            payment.save(update_fields=["gateway_order_id"])

        return Response({
            "payment_id": payment.id,
            "order_id": order["id"],
            "amount": order["amount"],
            "currency": order["currency"],
            "key": razorpay_client.auth[0],
        })


class VerifyPaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
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
            razorpay_client.utility.verify_payment_signature({
                "razorpay_order_id": data["razorpay_order_id"],
                "razorpay_payment_id": data["razorpay_payment_id"],
                "razorpay_signature": data["razorpay_signature"],
            })
        except Exception:
            return Response(
                {"error": "Signature verification failed"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            payment = Payment.objects.select_for_update().get(
                gateway_order_id=data["razorpay_order_id"]
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
                reference=f"payment:{payment.gateway_payment_id}",
            )

            # 2️⃣ Platform → Driver payout + commission split
            ride = Ride.objects.select_for_update().get(id=payment.ride_id)
            settle_driver_payout(
                ride=ride,
                payment=payment,
            )

        return Response({"status": "success"})


