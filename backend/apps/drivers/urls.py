# apps/drivers/urls.py

from django.urls import path
from .views import (
    DriverProfileView,
    GoOnlineView,
    GoOfflineView,
    UpdateLocationView,
    AcceptRideView,
    RejectRideView,
    DriverArrivedView,
    StartRideWithOTPView,
    MarkNoShowView,
)

urlpatterns = [
    path("me/", DriverProfileView.as_view()),
    path("online/", GoOnlineView.as_view()),
    path("offline/", GoOfflineView.as_view()),
    path("location/", UpdateLocationView.as_view()),

    path("rides/<int:ride_id>/accept/", AcceptRideView.as_view()),
    path("rides/<int:ride_id>/reject/", RejectRideView.as_view()),
    path("rides/<int:ride_id>/arrived/", DriverArrivedView.as_view()),
    path("rides/<int:ride_id>/start/", StartRideWithOTPView.as_view()),
    path("rides/<int:ride_id>/no-show/", MarkNoShowView.as_view()),
]
