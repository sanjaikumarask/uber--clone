from django.utils.timezone import now
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.users.permissions import IsAdmin
from apps.drivers.models import Driver
from apps.rides.models import Ride

from django.utils.timezone import now
from rest_framework.views import APIView
from rest_framework.response import Response

from apps.users.permissions import IsAdmin
from apps.drivers.models import Driver
from apps.rides.models import Ride


class AdminOverviewView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        today = now().date()

        return Response({
            "online_drivers": Driver.objects.filter(status=Driver.Status.ONLINE).count(),
            "busy_drivers": Driver.objects.filter(status=Driver.Status.BUSY).count(),
            "active_rides": Ride.objects.filter(
                status__in=[
                    Ride.Status.SEARCHING,
                    Ride.Status.OFFERED,
                    Ride.Status.ASSIGNED,
                    Ride.Status.ARRIVED,
                    Ride.Status.ONGOING,
                ]
            ).count(),
            "completed_today": Ride.objects.filter(
                status=Ride.Status.COMPLETED,
                updated_at__date=today,
            ).count(),
            "cancelled_today": Ride.objects.filter(
                status=Ride.Status.CANCELLED,
                updated_at__date=today,
            ).count(),
        })


class AdminLiveMapSnapshot(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        # 1. Active Drivers (exclude OFFLINE)
        drivers_qs = Driver.objects.exclude(status=Driver.Status.OFFLINE)
        drivers_data = []
        for d in drivers_qs:
            if d.last_lat and d.last_lng:
                drivers_data.append({
                    "id": d.id,
                    "lat": d.last_lat,
                    "lng": d.last_lng,
                    "status": d.status,
                    "phone": d.user.phone,
                })

        # 2. Active Rides
        active_statuses = [
            Ride.Status.SEARCHING,
            Ride.Status.OFFERED,
            Ride.Status.ASSIGNED,
            Ride.Status.ARRIVED,
            Ride.Status.ONGOING,
        ]
        rides_qs = Ride.objects.filter(status__in=active_statuses)
        rides_data = []
        for r in rides_qs:
            rides_data.append({
                "id": r.id,
                "status": r.status,
                "pickup": {"lat": r.pickup_lat, "lng": r.pickup_lng},
                "drop": {"lat": r.drop_lat, "lng": r.drop_lng},
                "driver_id": r.driver_id if r.driver else None,
            })

        return Response({
            "drivers": drivers_data,
            "rides": rides_data,
            "timestamp": now().isoformat(),
        })
