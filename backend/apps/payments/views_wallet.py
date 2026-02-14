# apps/payments/views_wallet.py
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.payments.services.wallet import (
    get_wallet_balance,
    get_held_balance,
    get_available_balance,
)


class WalletBalanceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        total = get_wallet_balance(user)
        held = get_held_balance(user)
        available = get_available_balance(user)

        return Response({
            "total_balance": str(total),
            "held_balance": str(held),
            "available_balance": str(available),
            "currency": "INR",
        })
