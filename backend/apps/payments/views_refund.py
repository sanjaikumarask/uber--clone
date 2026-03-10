import decimal
from decimal import Decimal

from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.payments.models import Payment
from apps.payments.services.refund import refund_payment


class RefundPaymentView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, payment_id):
        try:
            amount = Decimal(str(request.data.get("amount", "0")))
            reason = request.data.get("reason", "support_refund")
        except (TypeError, ValueError, decimal.InvalidOperation):
            return Response(
                {"error": "Invalid decimal amount"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from django.shortcuts import get_object_or_404
        payment = get_object_or_404(Payment, id=payment_id)

        try:
            result = refund_payment(
                payment=payment,
                amount=amount,
                reason=reason,
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "refund_id": result["refund_id"],
                "amount": str(result["amount"]),
                "status": result["status"],
            }
        )
