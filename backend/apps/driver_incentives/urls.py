from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    DriverIncentiveEarningViewSet,
    DriverIncentiveViewSet,
    IncentiveAnalyticsView,
    ReferralStatsView,
)

router = DefaultRouter()
router.register(r"incentives", DriverIncentiveViewSet, basename="incentive")
router.register(r"earnings", DriverIncentiveEarningViewSet, basename="earning")

urlpatterns = [
    path("referrals/", ReferralStatsView.as_view(), name="referral-stats"),
    path("analytics/", IncentiveAnalyticsView.as_view(), name="incentive-analytics"),
    path("", include(router.urls)),
]
