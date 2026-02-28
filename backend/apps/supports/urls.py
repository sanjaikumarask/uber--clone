# apps/supports/urls.py

from django.urls import path
from apps.supports.views import (
    CreateSupportTicketView,
    ResolveTicketView,
    TriggerSOSView,
    SupportTicketListView,
    SupportTicketDetailView,
    ResolveEmergencyView,
)

urlpatterns = [
    path("tickets/", SupportTicketListView.as_view(), name="ticket-list"),
    path("tickets/<int:pk>/", SupportTicketDetailView.as_view(), name="ticket-detail"),
    path("rides/<int:ride_id>/ticket/", CreateSupportTicketView.as_view()),
    path("rides/<int:ride_id>/sos/", TriggerSOSView.as_view()),
    # Renamed consistently
    path("rides/<int:ride_id>/tickets/", CreateSupportTicketView.as_view()),
    path("tickets/<int:ticket_id>/resolve/", ResolveTicketView.as_view()),
    path("emergencies/<int:emergency_id>/resolve/", ResolveEmergencyView.as_view()),
]
