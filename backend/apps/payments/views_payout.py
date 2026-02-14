from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Sum
from django.utils import timezone
from decimal import Decimal

from apps.payments.services.payout import request_driver_payout
from apps.payments.tasks import execute_driver_payout
from apps.payments.models import Payout
from apps.payments.services.wallet import get_available_balance


class DriverPayoutRequestView(APIView):
    """
    Driver Instant Withdrawal (Cash Out)
    GET: View Limit, Fee, Balance
    POST: Execute Payout
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if not hasattr(user, "driver"):
             return Response({"detail": "Driver access only"}, status=403)

        balance = get_available_balance(user)
        
        # 🛑 DAILY LIMIT LOGIC
        DAILY_LIMIT = Decimal("50000.00")
        today = timezone.now().date()
        
        used = Payout.objects.filter(
            driver=user, 
            created_at__date=today
        ).exclude(
            status=Payout.Status.FAILED
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal("0.00")
        
        remaining = max(DAILY_LIMIT - used, Decimal("0.00"))

        return Response({
            "available_balance": balance,
            "daily_limit": DAILY_LIMIT,
            "used_today": used,
            "remaining_limit": remaining,
            "fee_percent": 2.0, 
            "can_withdraw": balance >= 500 and remaining >= 500
        })

    def post(self, request):
        user = request.user

        if not hasattr(user, "driver"):
            return Response(
                {"detail": "Only drivers can request payout"},
                status=status.HTTP_403_FORBIDDEN,
            )

        amount = request.data.get("amount")

        # Default to full balance if amount not provided?
        # Or require amount? Let's default to full balance for "Cash Out All".
        if amount is None:
             amount = get_available_balance(user)
        else:
             amount = Decimal(str(amount))

        if amount < 500:
             return Response({"detail": "Minimum withdrawal is ₹500"}, status=400)

        try:
            # 1. Create Payout Request (Sync) - Checks Limit & Holds Funds
            payout = request_driver_payout(
                driver=user,
                amount=amount,
            )
            
            # 2. Mark for Immediate Processing
            payout.status = Payout.Status.PROCESSING
            payout.save(update_fields=["status"])
            
            # 3. Trigger Gateway (Async Task)
            execute_driver_payout.delay(payout_id=payout.id)

            return Response(
                {
                    "message": "Instant payout initiated",
                    "payout_id": payout.id,
                    "amount": str(payout.amount),
                    "fee": str(payout.fee),
                    "net_amount": str(payout.net_amount),
                    "status": "PROCESSING",
                    "reference": payout.reference,
                },
                status=status.HTTP_201_CREATED,
            )

        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {"detail": "System error processing payout"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
