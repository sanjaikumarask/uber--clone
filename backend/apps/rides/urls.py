from django.urls import path

from .admin_views import AdminRideActionView, AdminRidesListView
from .views import (
    AcceptRideView,
    ActiveRideView,
    CancelRideView,
    CompleteRideView,
    CreateRideView,
    DriverArrivedView,
    EstimateFareView,
    FareConfigView,
    MarkNoShowView,
    NearbyDriversView,
    RejectRideView,
    RideDetailView,
    RideFareBreakdownView,
    RideHistoryView,
    SubmitFeedbackView,
    TipView,
    UpdateDestinationView,
    VerifyOtpView,
    SimulateActionView,
)

urlpatterns = [
    # RIDER
    path("active/", ActiveRideView.as_view(), name="ride-active"),
    path("history/", RideHistoryView.as_view(), name="ride-history"),
    path("estimate-fare/", EstimateFareView.as_view(), name="ride-estimate"),
    path("nearby-drivers/", NearbyDriversView.as_view(), name="ride-nearby"),
    path("<int:ride_id>/feedback/", SubmitFeedbackView.as_view(), name="ride-feedback"),
    path("request/", CreateRideView.as_view(), name="ride-create"),
    path(
        "", CreateRideView.as_view(), name="ride-list"
    ),  # ✅ Supports POST /api/rides/
    # DRIVER
    path("<int:ride_id>/accept/", AcceptRideView.as_view(), name="ride-accept"),
    path("<int:ride_id>/reject/", RejectRideView.as_view(), name="ride-reject"),
    path("<int:ride_id>/arrived/", DriverArrivedView.as_view(), name="ride-arrive"),
    path("<int:ride_id>/start/", VerifyOtpView.as_view(), name="ride-start"),
    path("<int:ride_id>/no-show/", MarkNoShowView.as_view(), name="ride-no-show"),
    path("<int:ride_id>/complete/", CompleteRideView.as_view(), name="ride-complete"),
    path("<int:ride_id>/simulate-action/", SimulateActionView.as_view(), name="ride-simulate"),
    path("<int:ride_id>/", RideDetailView.as_view(), name="ride-detail"),
    # SHARED
    path("<int:ride_id>/cancel/", CancelRideView.as_view(), name="ride-cancel"),
    path(
        "<int:ride_id>/update-destination/",
        UpdateDestinationView.as_view(),
        name="ride-update-destination",
    ),
    path(
        "<int:ride_id>/fare-breakdown/",
        RideFareBreakdownView.as_view(),
        name="ride-fare-breakdown",
    ),
    path("<int:ride_id>/tip/", TipView.as_view(), name="ride-tip"),
    # CONFIG
    path("fare-config/", FareConfigView.as_view()),
    # ADMIN
    path("admin/rides/", AdminRidesListView.as_view()),
    path("admin/rides/actions/", AdminRideActionView.as_view()),
]
