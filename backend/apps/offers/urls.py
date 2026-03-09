from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AdminOfferViewSet,
    ApplyOfferView,
    OfferAnalyticsView,
    RiderOfferListView,
    ValidateOfferView,
)

router = DefaultRouter()
router.register("admin", AdminOfferViewSet, basename="admin-offers")

urlpatterns = [
    path("active/", RiderOfferListView.as_view()),
    path("apply/", ApplyOfferView.as_view()),
    path("validate/", ValidateOfferView.as_view()),
    path("admin/analytics/", OfferAnalyticsView.as_view()),
    path("", include(router.urls)),
]
