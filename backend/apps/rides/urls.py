from django.urls import path
from .views import (
    CreateRideView,
    VerifyOtpView,
    CompleteRideView,
    CancelRideView,
    ActiveRideView,
)

urlpatterns = [
    # CREATE / GET ACTIVE
    path("", CreateRideView.as_view(), name="rides-create"),

    # ACTIVE RIDE (READ ONLY)
    path("active/", ActiveRideView.as_view(), name="rides-active"),

    # RIDE ACTIONS
    path("<int:ride_id>/verify-otp/", VerifyOtpView.as_view()),
    path("<int:ride_id>/complete/", CompleteRideView.as_view()),
    path("<int:ride_id>/cancel/", CancelRideView.as_view()),
]
