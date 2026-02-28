# apps/admin_dashboard/urls.py
from django.urls import path
from .views import (
    AdminOverviewView,
    AdminLiveMapSnapshot,
    AdminAnalyticsView,
    AdminFareConfigView,
    AdminLiveRidesView,
    AdminPaymentStatusView,
    AdminAlertsView,
    AdminDriverListView,
    AdminDriverActionView,
)
from .views_admin import (
    AdminLedgerView,
    AdminPayoutListView,
    AdminPayoutActionView,
    AdminTicketsView,
    AdminResolveRideView,
)

urlpatterns = [
    # General Core
    path("overview/", AdminOverviewView.as_view()),
    path("live-map/snapshot/", AdminLiveMapSnapshot.as_view()),
    
    # Live Monitoring
    path("live-rides/", AdminLiveRidesView.as_view()),
    path("alerts/", AdminAlertsView.as_view()),
    
    # Financials & Config
    path("payments/status/", AdminPaymentStatusView.as_view()),
    path("analytics/", AdminAnalyticsView.as_view()),
    
    # Fare Configuration
    path("fare-config/", AdminFareConfigView.as_view()),
    path("fare-config/<int:pk>/", AdminFareConfigView.as_view()),
    
    # Driver Management
    path("drivers/", AdminDriverListView.as_view()),
    path("drivers/<int:driver_id>/action/", AdminDriverActionView.as_view()),
    
    # Missing Admin Endpoints
    path("payments/", AdminLedgerView.as_view()),
    path("payouts/", AdminPayoutListView.as_view()),
    path("payout/<str:action>/<int:id>/", AdminPayoutActionView.as_view()),
    path("tickets/", AdminTicketsView.as_view()),
    path("resolve-ride/", AdminResolveRideView.as_view()),
]
