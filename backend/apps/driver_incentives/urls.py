from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DriverIncentiveViewSet, DriverIncentiveEarningViewSet, IncentiveAnalyticsView

router = DefaultRouter()
router.register(r"incentives", DriverIncentiveViewSet, basename="incentive")
router.register(r"earnings", DriverIncentiveEarningViewSet, basename="earning")

urlpatterns = [
    path("analytics/", IncentiveAnalyticsView.as_view(), name="incentive-analytics"),
    path("", include(router.urls)),
]
