# apps/supports/urls.py

from django.urls import path
from apps.supports.views import (
    CreateSupportTicketView,
    ResolveTicketView,
)

urlpatterns = [
    path("rides/<int:ride_id>/ticket/", CreateSupportTicketView.as_view()),
    path("tickets/<int:ticket_id>/resolve/", ResolveTicketView.as_view()),
]
