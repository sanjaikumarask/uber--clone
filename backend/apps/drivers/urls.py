from django.urls import path
from .admin_views import (
    AdminDriversListView,
    AdminDriverDetailView,
    AdminDriverActionView,
    AdminDriverLevelView,
    AdminDriverLevelHistoryView,
    AdminPendingDocumentsView,
    AdminDocumentApprovalView,
    AdminPendingDriversView,
    AdminDriverRidesHistoryView,
)
from .views import (
    DriverProfileView,
    GoOnlineView,
    GoOfflineView,
    UpdateLocationView,
    DriverStatusView,
    DriverActiveRideView,
    DocumentUploadView,
    DriverRideHistoryView,
)
from apps.rides.views import NearbyDriversView

urlpatterns = [
    path("ride-history/", DriverRideHistoryView.as_view(), name="driver-ride-history-new"),
    # ── Driver self-service ──────────────────────────────────────────
    path("me/",          DriverProfileView.as_view(), name="driver-profile"),
    path("status/",      DriverStatusView.as_view(),  name="driver-status"),
    path("online/",      GoOnlineView.as_view(),       name="driver-online"),
    path("offline/",     GoOfflineView.as_view(),      name="driver-offline"),
    path("location/",    UpdateLocationView.as_view(), name="driver-location"),
    path("active-ride/", DriverActiveRideView.as_view(), name="driver-active-ride"),
    path("nearby/",      NearbyDriversView.as_view(),  name="nearby-drivers"),
    path("documents/upload/", DocumentUploadView.as_view(), name="driver-doc-upload"),

    # ── Admin: Driver list & metrics ─────────────────────────────────
    path("admin/drivers/",                         AdminDriversListView.as_view(),     name="admin-drivers-list"),
    path("admin/drivers/actions/",                 AdminDriverActionView.as_view(),    name="admin-drivers-action"),
    path("admin/drivers/<int:driver_id>/",         AdminDriverDetailView.as_view(),    name="admin-driver-detail"),
    path("admin/drivers/<int:driver_id>/level/",   AdminDriverLevelView.as_view(),     name="admin-driver-level"),
    path("admin/drivers/<int:driver_id>/level-history/", AdminDriverLevelHistoryView.as_view(), name="admin-driver-level-history"),
    path("admin/drivers/<int:driver_id>/history/", AdminDriverRidesHistoryView.as_view(), name="admin-driver-rides"),

    # ── Admin: Documents ─────────────────────────────────────────────
    path("admin/documents/pending/",              AdminPendingDocumentsView.as_view(), name="admin-docs-pending"),
    path("admin/drivers/pending/",                AdminPendingDriversView.as_view(),   name="admin-drivers-pending"),
    path("admin/documents/<int:doc_id>/approve/", AdminDocumentApprovalView.as_view(), name="admin-doc-approve"),
]