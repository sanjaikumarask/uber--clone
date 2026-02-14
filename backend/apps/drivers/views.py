from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from apps.users.permissions import IsDriver
from apps.drivers.models import Driver
from apps.rides.models import Ride

# =====================================================
# DRIVER PROFILE
# =====================================================
class DriverProfileView(APIView):
    permission_classes = [IsDriver]

    def get(self, request):
        driver = request.user.driver
        return Response({
            "id": driver.id,
            "status": driver.status,
            # Add other stats if needed
        })

# =====================================================
# GO ONLINE
# =====================================================
class GoOnlineView(APIView):
    permission_classes = [IsDriver]

    def post(self, request):
        driver = request.user.driver
        driver.status = Driver.Status.ONLINE
        driver.save(update_fields=["status"])
        return Response({"status": driver.status})

# =====================================================
# GO OFFLINE
# =====================================================
class GoOfflineView(APIView):
    permission_classes = [IsDriver]

    def post(self, request):
        driver = request.user.driver

        # Check if driver has an active ride
        if Ride.objects.filter(
            driver=driver,
            status__in=[
                Ride.Status.ASSIGNED,
                Ride.Status.ARRIVED,
                Ride.Status.ONGOING,
            ],
        ).exists():
            return Response(
                {"error": "Cannot go offline during active ride"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        driver.status = Driver.Status.OFFLINE
        driver.save(update_fields=["status"])
        return Response({"status": driver.status})

# =====================================================
# UPDATE LOCATION
# =====================================================
class UpdateLocationView(APIView):
    permission_classes = [IsDriver]

    def post(self, request):
        driver = request.user.driver
        try:
            lat = float(request.data["lat"])
            lng = float(request.data["lng"])
            
            # Validate coordinates
            if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
                return Response(
                    {"error": "Invalid coordinates"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            driver.last_lat = lat
            driver.last_lng = lng
        except (KeyError, ValueError):
            return Response(
                {"error": "lat and lng required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        driver.save(update_fields=["last_lat", "last_lng"])
        
        # Broadcast to Admin Live Map
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "admin_live_map",
            {
                "type": "driver.location.update",
                "data": {
                    "id": driver.id,
                    "lat": driver.last_lat,
                    "lng": driver.last_lng,
                    "status": driver.status,
                    "phone": driver.user.phone,
                },
            },
        )

        return Response({"ok": True})


# =====================================================
# UNIFIED STATUS UPDATE
# =====================================================
class DriverStatusView(APIView):
    permission_classes = [IsDriver]

    def post(self, request):
        driver = request.user.driver
        new_status = request.data.get("status", "").upper()

        if new_status not in ["ONLINE", "OFFLINE"]:
            return Response(
                {"error": "Invalid status. Use ONLINE or OFFLINE"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check if driver has an active ride when going offline
        if new_status == "OFFLINE":
            if Ride.objects.filter(
                driver=driver,
                status__in=[
                    Ride.Status.ASSIGNED,
                    Ride.Status.ARRIVED,
                    Ride.Status.ONGOING,
                ],
            ).exists():
                return Response(
                    {"error": "Cannot go offline during active ride"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        driver.status = new_status
        driver.save(update_fields=["status"])
        return Response({"status": driver.status})


# =====================================================
# DRIVER ACTIVE RIDE
# =====================================================
class DriverActiveRideView(APIView):
    """Get the driver's current active ride"""
    permission_classes = [IsDriver]
    
    def get(self, request):
        driver = request.user.driver
        
        # Find active ride for this driver
        ride = Ride.objects.filter(
            driver=driver,
            status__in=[
                Ride.Status.ASSIGNED,
                Ride.Status.ARRIVED,
                Ride.Status.ONGOING,
            ]
        ).first()
        
        if not ride:
            return Response({"ride": None})
        
        from apps.rides.serializers import RideDetailSerializer
        serializer = RideDetailSerializer(ride)
        return Response(serializer.data)
