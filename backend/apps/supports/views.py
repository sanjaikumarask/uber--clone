# apps/support/views.py

from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.rides.models import Ride
from apps.supports.models import SupportTicket
from apps.supports.services import (
    reject_ticket,
    resolve_with_refund,
)

from .serializers import SupportTicketSerializer


class CreateSupportTicketView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, ride_id):
        ride = get_object_or_404(Ride, id=ride_id)

        from django.core.exceptions import ValidationError as DjangoValidationError

        try:
            from apps.supports.services import (  # Import here to avoid circular
                open_support_ticket,
            )

            ticket = open_support_ticket(
                ride=ride,
                user=request.user,
                reason=request.data.get("reason"),
                description=request.data.get("description", ""),
            )
        except DjangoValidationError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"ticket_id": ticket.id, "status": ticket.status},
            status=status.HTTP_201_CREATED,
        )


class SupportTicketListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SupportTicketSerializer

    def get_queryset(self):
        return SupportTicket.objects.filter(user=self.request.user).order_by(
            "-created_at"
        )


class SupportTicketDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SupportTicketSerializer

    def get_queryset(self):
        return SupportTicket.objects.filter(user=self.request.user)


class ResolveTicketView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, ticket_id):
        ticket = get_object_or_404(SupportTicket, id=ticket_id)

        if not request.user.is_admin:
            return Response({"error": "Admin only"}, status=403)

        refund_amount = request.data.get("refund_amount")
        note = request.data.get("note", "")

        if refund_amount:
            from decimal import Decimal

            try:
                resolve_with_refund(
                    ticket=ticket,
                    admin=request.user,
                    refund_amount=Decimal(str(refund_amount)),
                    reason_note=note,
                )
            except Exception as e:
                return Response({"error": f"Refund failed: {e!s}"}, status=400)
        else:
            reject_ticket(ticket=ticket, admin=request.user, note=note)

        return Response({"status": ticket.status})


class TriggerSOSView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, ride_id):
        ride = get_object_or_404(Ride, id=ride_id)

        # Check if user is part of the ride
        if ride.rider != request.user and (
            not ride.driver or ride.driver.user != request.user
        ):
            return Response(
                {"error": "No permission to trigger SOS for this ride"}, status=403
            )

        lat = request.data.get("lat")
        lng = request.data.get("lng")

        if not lat or not lng:
            return Response({"error": "Location data required for SOS"}, status=400)

        from apps.supports.models import Emergency

        emergency = Emergency.objects.create(
            ride=ride, user=request.user, lat=float(lat), lng=float(lng)
        )

        # Broadcast to Admin and specific Ride Group
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer

        channel_layer = get_channel_layer()

        event_payload = {
            "type": "sos_alert",
            "data": {
                "emergency_id": emergency.id,
                "ride_id": ride.id,
                "user_id": request.user.id,
                "user_name": request.user.get_full_name() or request.user.phone,
                "lat": emergency.lat,
                "lng": emergency.lng,
                "created_at": str(emergency.created_at),
            },
        }

        # 1. To Admin
        async_to_sync(channel_layer.group_send)(
            "admin_live_map",
            {
                "type": "admin_generic_event",
                "event": "SOS_ALERT",
                "data": event_payload["data"],
            },
        )

        # 2. To Ride Group (Alerts the other party)
        async_to_sync(channel_layer.group_send)(f"ride_{ride.id}", event_payload)

        return Response({"success": True, "emergency_id": emergency.id})


class ResolveEmergencyView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, emergency_id):
        from apps.supports.models import Emergency

        emergency = get_object_or_404(Emergency, id=emergency_id)

        if not request.user.is_staff and not request.user.is_superuser:
            return Response({"error": "Admin only"}, status=403)

        note = request.data.get("note", "")
        status_code = request.data.get("status", Emergency.Status.RESOLVED)

        emergency.resolve(admin_user=request.user, note=note, status=status_code)

        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"ride_{emergency.ride_id}",
            {
                "type": "sos_resolved",
                "data": {"emergency_id": emergency.id, "status": emergency.status},
            },
        )

        return Response({"status": emergency.status})
