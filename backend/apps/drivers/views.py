from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone

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
        from apps.drivers.models import DriverStats
        stats, _ = DriverStats.objects.get_or_create(driver=driver)
        
        return Response({
            "id": driver.id,
            "status": driver.status,
            "level": driver.level,
            "is_verified": driver.is_verified,
            "total_rides": driver.total_rides,
            "completed_rides": stats.completed_rides,
            "avg_rating": stats.avg_rating,
            "acceptance_rate": stats.acceptance_rate,
            "weekly_rides": stats.weekly_rides,
        })


# =====================================================
# GO ONLINE
# =====================================================
class GoOnlineView(APIView):
    permission_classes = [IsDriver]

    def post(self, request):
        driver = request.user.driver
        
        # ── Guard: Suspension Check ──
        from apps.drivers.models import DriverStats
        stats, _ = DriverStats.objects.get_or_create(driver=driver)
        if stats.is_suspended and stats.suspended_until and stats.suspended_until > timezone.now():
            return Response({
                "error": "Account suspended",
                "suspended_until": stats.suspended_until.isoformat()
            }, status=status.HTTP_403_FORBIDDEN)

        driver.status = Driver.Status.ONLINE
        driver.save(update_fields=["status"])

        # 🚀 Broadcast status change to Admin Dashboard
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        channel_layer = get_channel_layer()

        async_to_sync(channel_layer.group_send)(
            "admin_live_map",
            {
                "type": "driver_location_update",
                "data": {
                    "driver_id": driver.id,
                    "lat": driver.last_lat,
                    "lng": driver.last_lng,
                    "status": driver.status,
                    "ts": int(timezone.now().timestamp()),
                },
            },
        )

        return Response({"status": driver.status})


# =====================================================
# GO OFFLINE
# =====================================================
class GoOfflineView(APIView):
    permission_classes = [IsDriver]

    def post(self, request):
        driver = request.user.driver

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

        # 🚀 Broadcast status change to Admin Dashboard
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        channel_layer = get_channel_layer()

        async_to_sync(channel_layer.group_send)(
            "admin_live_map",
            {
                "type": "driver_location_update",
                "data": {
                    "driver_id": driver.id,
                    "lat": driver.last_lat,
                    "lng": driver.last_lng,
                    "status": driver.status,
                    "ts": int(timezone.now().timestamp()),
                },
            },
        )

        return Response({"status": driver.status})


# =====================================================
# UPDATE LOCATION
# =====================================================
class UpdateLocationView(APIView):
    permission_classes = [IsDriver]

    def post(self, request):
        driver = request.user.driver

        # Validate input
        try:
            lat = float(request.data["lat"])
            lng = float(request.data["lng"])
            heading = float(request.data.get("heading", 0))
            speed_kmh = float(request.data.get("speed_kmh", 0))

            if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
                return Response(
                    {"error": "Invalid coordinates"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except (KeyError, ValueError):
            return Response(
                {"error": "lat and lng required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Save driver location
        driver.last_lat = lat
        driver.last_lng = lng
        driver.save(update_fields=["last_lat", "last_lng"])
        
        # ── Update Redis Geo ──
        from apps.drivers.redis import update_driver_location
        update_driver_location(driver.id, lat, lng)

        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        channel_layer = get_channel_layer()

        # -------------------------------------------------
        # Fetch Active Ride Info
        # -------------------------------------------------
        active_ride = Ride.objects.filter(
            driver=driver,
            status__in=[
                Ride.Status.ASSIGNED,
                Ride.Status.ARRIVED,
                Ride.Status.ONGOING,
            ],
        ).select_related('rider').first()

        ride_data = None
        deviation_alert = False
        
        if active_ride:
            ride_data = {
                "id": active_ride.id,
                "status": active_ride.status,
                "pickup": {"lat": active_ride.pickup_lat, "lng": active_ride.pickup_lng},
                "dropoff": {"lat": active_ride.drop_lat, "lng": active_ride.drop_lng},
                "pickup_address": active_ride.pickup_address,
                "drop_address": active_ride.drop_address,
                "polyline": active_ride.planned_route_polyline,
                "rider_name": f"{active_ride.rider.first_name} {active_ride.rider.last_name}",
                "vehicle_type": active_ride.vehicle_type,
            }

            # 🚨 Route Deviation Check (Backend side)
            if active_ride.status == Ride.Status.ONGOING and active_ride.planned_route_polyline:
                from apps.rides.services.deviation import check_route_deviation
                is_deviated, dist_m = check_route_deviation(driver, active_ride, lat, lng)
                deviation_alert = is_deviated

        # -------------------------------------------------
        # 1️⃣ Admin Live Map Broadcast
        # -------------------------------------------------
        async_to_sync(channel_layer.group_send)(
            "admin_live_map",
            {
                "type": "driver_location_update",
                "data": {
                    "driver_id": driver.id,
                    "name": f"{driver.user.first_name} {driver.user.last_name}",
                    "phone": driver.user.phone,
                    "lat": lat,
                    "lng": lng,
                    "heading": heading,
                    "speed_kmh": speed_kmh,
                    "status": driver.status,
                    "ts": int(timezone.now().timestamp()),
                    "ride": ride_data,
                    "deviation": deviation_alert, # Can be expanded with real logic
                },
            },
        )

        # -------------------------------------------------
        # 2️⃣ Rider Broadcast
        # -------------------------------------------------
        if active_ride:
            async_to_sync(channel_layer.group_send)(
                f"ride_{active_ride.id}",
                {
                    "type": "ride_update",
                    "event": "DRIVER_LOCATION_UPDATED",
                    "data": {
                        "lat": lat,
                        "lng": lng,
                        "heading": heading,
                        "speed_kmh": speed_kmh,
                        "ts": int(timezone.now().timestamp()),
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

        if new_status == "ONLINE":
            from apps.drivers.models import DriverStats
            stats, _ = DriverStats.objects.get_or_create(driver=driver)
            if stats.is_suspended and stats.suspended_until and stats.suspended_until > timezone.now():
                return Response({
                    "error": "Account suspended",
                    "suspended_until": stats.suspended_until.isoformat()
                }, status=status.HTTP_403_FORBIDDEN)

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

        # 🚀 Broadcast status change to Admin Dashboard
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        channel_layer = get_channel_layer()

        # ⚡ CRITICAL: Add/remove from Redis GEO so matching engine can find them
        if new_status == "ONLINE" and driver.last_lat and driver.last_lng:
            from apps.drivers.services.geo import add_driver_to_geo
            add_driver_to_geo(
                driver_id=driver.id,
                lat=float(driver.last_lat),
                lng=float(driver.last_lng),
            )
        elif new_status == "OFFLINE":
            from apps.drivers.services.geo import remove_driver_from_geo
            remove_driver_from_geo(driver_id=driver.id)

        async_to_sync(channel_layer.group_send)(
            "admin_live_map",
            {
                "type": "driver_location_update",
                "data": {
                    "driver_id": driver.id,
                    "lat": driver.last_lat,
                    "lng": driver.last_lng,
                    "status": driver.status,
                    "ts": int(timezone.now().timestamp()),
                },
            },
        )

        return Response({"status": driver.status})



# =====================================================
# DRIVER ACTIVE RIDE
# =====================================================
class DriverActiveRideView(APIView):
    permission_classes = [IsDriver]

    def get(self, request):
        driver = request.user.driver

        ride = Ride.objects.filter(
            driver=driver,
            status__in=[
                Ride.Status.ASSIGNED,
                Ride.Status.ARRIVED,
                Ride.Status.ONGOING,
            ],
        ).first()

        if not ride:
            return Response({"ride": None})

        from apps.rides.serializers import RideDetailSerializer
        return Response(RideDetailSerializer(ride).data)

class DocumentUploadView(APIView):
    permission_classes = [IsDriver]

    def get(self, request):
        from .models import DriverDocument
        from .serializers import DriverDocumentSerializer
        docs = DriverDocument.objects.filter(driver=request.user.driver)
        return Response(DriverDocumentSerializer(docs, many=True, context={'request': request}).data)

    def post(self, request):
        from .models import DriverDocument
        driver = request.user.driver
        doc_type = request.data.get("document_type")
        file = request.data.get("file")

        if not doc_type or not file:
            return Response({"error": "document_type and file are required"}, status=400)

        if doc_type not in [t[0] for t in DriverDocument.Type.choices]:
            return Response({"error": "Invalid document type"}, status=400)

        # Handle both JSON (url string) and Multipart (file object)
        update_data = {
            "status": DriverDocument.Status.PENDING,
            "rejection_reason": ""
        }
        
        if hasattr(file, 'read'): # It's a file object
            update_data["image"] = file
        else: # It's a string path/URL
            update_data["file_path"] = file

        # Ensure directory exists and is writable
        import os
        from django.conf import settings
        media_dir = os.path.join(settings.MEDIA_ROOT, 'driver_docs')
        try:
            os.makedirs(media_dir, exist_ok=True)
            # Try to set permissions if possible
            try:
                os.chmod(media_dir, 0o777)
            except:
                pass
        except Exception as e:
            print(f"[ERROR] Failed to create media directory: {e}")

        doc, created = DriverDocument.objects.update_or_create(
            driver=driver,
            document_type=doc_type,
            defaults=update_data
        )

        return Response({
            "id": doc.id,
            "status": doc.status,
            "document_type": doc.document_type,
            "created": created
        })

class DriverRideHistoryView(APIView):
    permission_classes = [IsDriver]

    def get(self, request):
        from apps.rides.serializers import RideDetailSerializer
        from apps.rides.models import Ride
        
        # Get past rides for this driver (assigned, arrived, ongoing, completed, cancelled)
        # Exclude only searching/offered which are pre-assignment
        rides = Ride.objects.filter(
            driver=request.user.driver
        ).exclude(
            status__in=[Ride.Status.SEARCHING, Ride.Status.OFFERED]
        ).select_related("rider").order_by("-created_at")[:50]
        
        serializer = RideDetailSerializer(rides, many=True)
        return Response(serializer.data)
