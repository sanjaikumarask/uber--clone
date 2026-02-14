from django.urls import path
from .admin_views import AdminDriversListView, AdminDriverActionView
from .views import (
    DriverProfileView,
    GoOnlineView,
    GoOfflineView,
    UpdateLocationView,
    DriverStatusView,
    DriverActiveRideView,
)

urlpatterns = [
    path("me/", DriverProfileView.as_view(), name="driver-profile"),
    path("status/", DriverStatusView.as_view(), name="driver-status"),
    path("online/", GoOnlineView.as_view(), name="driver-online"),
    path("offline/", GoOfflineView.as_view(), name="driver-offline"),
    path("location/", UpdateLocationView.as_view(), name="driver-location"),
    path("active-ride/", DriverActiveRideView.as_view(), name="driver-active-ride"),
    path("admin/drivers/", AdminDriversListView.as_view()),
    path("admin/drivers/actions/", AdminDriverActionView.as_view()),
]