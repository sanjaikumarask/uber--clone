from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.payments.services.wallet import get_wallet_balance


class WalletBalanceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        balance = get_wallet_balance(request.user)

        return Response({
            "balance": str(balance),
            "currency": "INR",
        })
