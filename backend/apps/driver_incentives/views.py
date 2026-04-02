from django.db.models import Count, Sum
from django.utils import timezone
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.permissions import IsAdmin

from .models import DriverIncentive, DriverIncentiveEarning
from .serializers import DriverIncentiveEarningSerializer, DriverIncentiveSerializer


class DriverIncentiveViewSet(viewsets.ModelViewSet):
    """
    Admin: full CRUD on incentives.
    Driver: read-only list of active incentives.
    """

    queryset = DriverIncentive.objects.all()
    serializer_class = DriverIncentiveSerializer

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAdmin()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        # Staff/Admins see everything
        if user.is_staff or getattr(user, "role", "") == "admin":
            return DriverIncentive.objects.all().order_by("-created_at")
        # Drivers see all active incentives
        return DriverIncentive.objects.filter(is_active=True).order_by("-created_at")

    @action(detail=True, methods=["post"], permission_classes=[IsAdmin])
    def deactivate(self, request, pk=None):
        incentive = self.get_object()
        incentive.is_active = False
        incentive.save(update_fields=["is_active"])
        return Response({"status": "deactivated"})

    @action(detail=True, methods=["post"], permission_classes=[IsAdmin])
    def activate(self, request, pk=None):
        incentive = self.get_object()
        incentive.is_active = True
        incentive.save(update_fields=["is_active"])
        return Response({"status": "activated"})


class DriverIncentiveEarningViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Earnings history — drivers see their own, admins see all.
    """

    queryset = DriverIncentiveEarning.objects.all()
    serializer_class = DriverIncentiveEarningSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or getattr(user, "role", "") == "admin":
            return DriverIncentiveEarning.objects.all().order_by("-created_at")
        if hasattr(user, "driver"):
            return DriverIncentiveEarning.objects.filter(driver=user.driver).order_by(
                "-created_at"
            )
        return DriverIncentiveEarning.objects.none()


class IncentiveAnalyticsView(APIView):
    """
    Admin analytics: totals, per-incentive breakdown, daily trends.
    """

    permission_classes = [IsAdmin]

    def get(self, request):
        total_paid = (
            DriverIncentiveEarning.objects.aggregate(total=Sum("bonus_amount"))["total"]
            or 0
        )

        per_incentive = (
            DriverIncentiveEarning.objects.values(
                "incentive__id", "incentive__title", "incentive__type"
            )
            .annotate(
                total_paid=Sum("bonus_amount"),
                redemption_count=Count("id"),
            )
            .order_by("-total_paid")
        )

        # Daily incentive payout for last 7 days
        from django.db.models.functions import TruncDate

        daily = (
            DriverIncentiveEarning.objects.filter(
                created_at__date__gte=(
                    timezone.now().date() - timezone.timedelta(days=7)
                )
            )
            .annotate(date=TruncDate("created_at"))
            .values("date")
            .annotate(total=Sum("bonus_amount"))
            .order_by("date")
        )

        return Response(
            {
                "total_incentives_paid": float(total_paid),
                "per_incentive_breakdown": list(per_incentive),
                "daily_last_7_days": list(daily),
            }
        )


class ReferralStatsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        # Ensure referral code exists
        if not user.referral_code:
            import random, string
            user.referral_code = 'TRIPZO-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            user.save(update_fields=['referral_code'])

        referrals = user.referrals.all()

        return Response({
            "total_referrals": referrals.count(),
            "earned_amount": 0,  # Placeholder
            "pending_amount": 0, # Placeholder
            "referral_code": user.referral_code,
            "referrals": [
                {
                    "name": f"{r.first_name} {r.last_name}".strip() or r.phone,
                    "joined_date": r.date_joined.strftime("%Y-%m-%d"),
                    "status": "Completed" if r.is_active else "Pending",
                    "reward": 50
                } for r in referrals
            ]
        })
