# apps/support/views.py

from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from apps.supports.models import SupportTicket
from apps.supports.services import (
    open_support_ticket,
    resolve_with_refund,
    reject_ticket,
)
from apps.rides.models import Ride


class CreateSupportTicketView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, ride_id):
        ride = get_object_or_404(Ride, id=ride_id)

        ticket = open_support_ticket(
            ride=ride,
            user=request.user,
            reason=request.data.get("reason"),
            description=request.data.get("description", ""),
        )

        return Response(
            {"ticket_id": ticket.id, "status": ticket.status},
            status=status.HTTP_201_CREATED,
        )


class ResolveTicketView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, ticket_id):
        ticket = get_object_or_404(SupportTicket, id=ticket_id)

        if not request.user.is_admin:
            return Response({"error": "Admin only"}, status=403)

        refund_amount = request.data.get("refund_amount")
        note = request.data.get("note", "")

        if refund_amount:
            resolve_with_refund(
                ticket=ticket,
                admin=request.user,
                refund_amount=refund_amount,
                reason_note=note,
            )
        else:
            reject_ticket(ticket=ticket, admin=request.user, note=note)

        return Response({"status": ticket.status})
