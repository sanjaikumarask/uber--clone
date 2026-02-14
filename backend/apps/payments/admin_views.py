from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from apps.users.permissions import IsAdmin
from apps.payments.models import LedgerEntry, Payout
from apps.payments.tasks import execute_driver_payout
from apps.payments.services.invariants import assert_user_ledger



class AdminPaymentsView(APIView):
    """
    Admin ledger audit view (read-only)
    """
    permission_classes = [IsAdmin]

    def get(self, request):
        entries = (
            LedgerEntry.objects
            .select_related("user")
            .order_by("-created_at")[:200]
        )

        data = [
            {
                "id": e.id,
                "user_id": e.user_id,
                "ride_id": e.ride_id,
                "amount": str(e.amount),
                "type": e.entry_type,
                "reason": e.reason,
                "reference": e.reference,
                "created_at": e.created_at,
            }
            for e in entries
        ]

        return Response(data)


class AdminApprovePayoutView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, payout_id):
        payout = get_object_or_404(Payout, id=payout_id)

        if payout.status != Payout.Status.REQUESTED:
            return Response({"error": "Invalid state"}, status=400)

        payout.status = Payout.Status.PROCESSING
        payout.save(update_fields=["status"])

        # ⚠️ Trigger Razorpay transfer async here
        return Response({"status": "processing"})


class AdminRejectPayoutView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, payout_id):
        payout = get_object_or_404(Payout, id=payout_id)

        if payout.status != Payout.Status.REQUESTED:
            return Response({"error": "Invalid state"}, status=400)

        payout.status = Payout.Status.FAILED
        payout.save(update_fields=["status"])

        return Response({"status": "rejected"})



class AdminApprovePayoutView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, payout_id):
        payout = get_object_or_404(Payout, id=payout_id)

        if payout.status != Payout.Status.REQUESTED:
            return Response({"error": "Invalid state"}, status=400)

        payout.status = Payout.Status.PROCESSING
        payout.save(update_fields=["status"])

        # 🔥 ASYNC PAYOUT
        execute_driver_payout.delay(payout.id)

        return Response({"status": "processing"})


class AdminLedgerCheckView(APIView):
    """
    Admin tool: validate ledger invariants for a user
    """
    permission_classes = [IsAdmin]

    def post(self, request):
        user_id = request.data.get("user_id")

        if not user_id:
            return Response(
                {"error": "user_id is required"},
                status=400,
            )

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"},
                status=404,
            )

        # 🔍 Ledger invariant check
        assert_user_ledger(user)

        return Response(
            {
                "status": "ok",
                "user_id": user.id,
                "message": "Ledger is consistent",
            }
        )