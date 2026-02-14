from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Count
from apps.users.permissions import IsAdmin
from apps.drivers.models import Driver, DriverStats

class AdminDriversListView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        drivers = (
            Driver.objects
            .select_related("user")
            .prefetch_related("stats")
        )

        data = []

        for d in drivers:
            stats = getattr(d, "stats", None)

            data.append({
                "driver_id": d.id,
                "phone": d.user.phone,
                "status": d.status,
                "lat": d.last_lat,
                "lng": d.last_lng,
                "total_rides": stats.total_rides if stats else 0,
                "avg_rating": stats.avg_rating if stats else 5.0,
                "rejections_today": stats.rejection_count_today if stats else 0,
                "is_suspended": stats.is_suspended if stats else False,
                "updated_at": d.updated_at,
            })

        return Response(data)


class AdminDriverActionView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request):
        driver_id = request.data.get("driver_id")
        action = request.data.get("action")  # "suspend" | "unsuspend"

        if not driver_id or action not in ["suspend", "unsuspend"]:
            return Response({"error": "Invalid params"}, status=400)

        try:
            driver = Driver.objects.get(id=driver_id)
            stats, _ = DriverStats.objects.get_or_create(driver=driver)

            if action == "suspend":
                stats.is_suspended = True
                driver.status = Driver.Status.OFFLINE  # Force offline
                driver.save()
            else:
                stats.is_suspended = False

            stats.save()
            return Response({"success": True, "is_suspended": stats.is_suspended})

        except Driver.DoesNotExist:
            return Response({"error": "Driver not found"}, status=404)
