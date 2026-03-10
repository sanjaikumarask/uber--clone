# apps/admin_dashboard/urls.py
from django.urls import path

from apps.rides.admin_views import ResolveRideView

from .views import (
    AdminAlertsView,
    AdminAnalyticsView,
    AdminDriverActionView,
    AdminDriverListView,
    AdminFareConfigView,
    AdminLiveMapSnapshot,
    AdminLiveRidesView,
    AdminOverviewView,
    AdminPaymentStatusView,
    AdminSystemLogsView,
)
from .views_admin import (
    AdminLedgerView,
    AdminPayoutActionView,
    AdminPayoutListView,
    AdminTicketsView,
)

urlpatterns = [
    # General Core
    path("overview/", AdminOverviewView.as_view(), name="admin-overview"),
    path("live-map/snapshot/", AdminLiveMapSnapshot.as_view(), name="admin-live-map"),
    # Live Monitoring
    path("live-rides/", AdminLiveRidesView.as_view(), name="admin-live-rides"),
    path("alerts/", AdminAlertsView.as_view(), name="admin-alerts"),
    # Financials & Config
    path("payments/status/", AdminPaymentStatusView.as_view(), name="admin-payment-status"),
    path("analytics/", AdminAnalyticsView.as_view(), name="admin-analytics"),
    # Fare Configuration
    path("fare-config/", AdminFareConfigView.as_view()),
    path("fare-config/<int:pk>/", AdminFareConfigView.as_view()),
    # Driver Management
    path("drivers/", AdminDriverListView.as_view()),
    path("drivers/<int:driver_id>/action/", AdminDriverActionView.as_view()),
    # Missing Admin Endpoints
    path("payments/", AdminLedgerView.as_view(), name="admin-ledger"),
    path("payouts/", AdminPayoutListView.as_view(), name="admin-payouts"),
    path("payout/<str:action>/<int:payout_id>/", AdminPayoutActionView.as_view(), name="admin-payout-action"),
    path("tickets/", AdminTicketsView.as_view(), name="admin-tickets"),
    path("resolve-ride/", ResolveRideView.as_view()),
    path("logs/", AdminSystemLogsView.as_view()),
]
