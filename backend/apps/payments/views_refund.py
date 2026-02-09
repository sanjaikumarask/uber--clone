from decimal import Decimal
from rest_framework.views import APIView
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework import status

from apps.payments.models import Payment
from apps.payments.services.refund import refund_payment


class RefundPaymentView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, payment_id):
        try:
            amount = Decimal(request.data.get("amount"))
            reason = request.data.get("reason", "support_refund")
        except Exception:
            return Response(
                {"error": "Invalid payload"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payment = Payment.objects.get(id=payment_id)

        try:
            result = refund_payment(
                payment=payment,
                amount=amount,
                reason=reason,
                initiated_by=request.user,
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
