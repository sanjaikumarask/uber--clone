from django.urls import path
from .views import (
    CreateRideView,
    RideDetailView,
    AcceptRideView,
    RejectRideView,
    DriverArrivedView,
    VerifyOtpView,
    CompleteRideView,
    MarkNoShowView,
    CancelRideView,
    UpdateDestinationView,
    ActiveRideView,
    RideHistoryView,
    SubmitFeedbackView,
    EstimateFareView,
    NearbyDriversView,
    FareConfigView,
    RideFareBreakdownView,
    TipView,
)
from .admin_views import AdminRidesListView, AdminRideActionView

urlpatterns = [
    # RIDER
    path("active/", ActiveRideView.as_view()),
    path("history/", RideHistoryView.as_view()),
    path("estimate-fare/", EstimateFareView.as_view()),
    path("nearby-drivers/", NearbyDriversView.as_view()),
    path("<int:ride_id>/feedback/", SubmitFeedbackView.as_view()),
    path("request/", CreateRideView.as_view()),
    path("", CreateRideView.as_view()),  # ✅ Supports POST /api/rides/
    # DRIVER
    path("<int:ride_id>/accept/", AcceptRideView.as_view()),
    path("<int:ride_id>/reject/", RejectRideView.as_view()),
    path("<int:ride_id>/arrived/", DriverArrivedView.as_view()),
    path("<int:ride_id>/start/", VerifyOtpView.as_view()),  # Verifies OTP to start ride
    path("<int:ride_id>/no-show/", MarkNoShowView.as_view()),
    path("<int:ride_id>/complete/", CompleteRideView.as_view()),

    path("<int:ride_id>/", RideDetailView.as_view()),

    # SHARED
    path("<int:ride_id>/cancel/", CancelRideView.as_view()),
    path("<int:ride_id>/update-destination/", UpdateDestinationView.as_view()),
    path("<int:ride_id>/fare-breakdown/", RideFareBreakdownView.as_view()),
    path("<int:ride_id>/tip/", TipView.as_view()),

    # CONFIG
    path("fare-config/", FareConfigView.as_view()),

    # ADMIN
    path("admin/rides/", AdminRidesListView.as_view()),
    path("admin/rides/actions/", AdminRideActionView.as_view()),
]
