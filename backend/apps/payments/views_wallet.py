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

class WalletTransactionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.payments.models import LedgerEntry
        # Get last 50 transactions for the user
        entries = LedgerEntry.objects.filter(user=request.user).order_by("-created_at")[:50]
        
        data = []
        for e in entries:
            data.append({
                "id": e.id,
                "amount": str(e.amount),
                "type": e.entry_type,
                "reason": e.reason,
                "reference": e.reference,
                "created_at": e.created_at.isoformat(),
            })
            
        return Response(data)
