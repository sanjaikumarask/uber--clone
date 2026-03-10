from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.payments.models import LedgerEntry, Payout
from apps.payments.services.invariants import assert_user_ledger
from apps.payments.tasks import execute_driver_payout
from apps.users.models import User
from apps.users.permissions import IsAdmin


class AdminPaymentsView(APIView):
    """
    Admin ledger audit view
    """

    permission_classes = [IsAdmin]

    def get(self, request):
        entries = LedgerEntry.objects.select_related("user").order_by("-created_at")[
            :200
        ]

        data = [
            {
                "id": e.id,
                "user_phone": e.user.phone,
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


class AdminPayoutListView(APIView):
    """
    List payout requests
    """

    permission_classes = [IsAdmin]

    def get(self, request):
        payouts = Payout.objects.select_related("driver").order_by("-created_at")[:100]

        data = [
            {
                "id": p.id,
                "driver_phone": p.driver.phone,
                "amount": str(p.amount),
                "status": p.status,
                "reference": p.reference,  # ✅ FIXED
                "created_at": p.created_at,
            }
            for p in payouts
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

        # 🔥 async payout execution
        execute_driver_payout.delay(payout.id)

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


class AdminLedgerCheckView(APIView):
    """
    Validate ledger invariants for a user
    """

    permission_classes = [IsAdmin]

    def post(self, request):
        user_id = request.data.get("user_id")

        if not user_id:
            return Response({"error": "user_id is required"}, status=400)

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)

        assert_user_ledger(user)

        return Response(
            {
                "status": "ok",
                "user_id": user.id,
                "message": "Ledger is consistent",
            }
        )
