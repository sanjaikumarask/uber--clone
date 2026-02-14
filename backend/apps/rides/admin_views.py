from rest_framework.views import APIView
from rest_framework.response import Response
from apps.users.permissions import IsAdmin
from apps.rides.models import Ride
from django.utils import timezone

class AdminRidesListView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        rides = Ride.objects.select_related("rider", "driver").order_by("-created_at")[:50]
        data = []
        for r in rides:
            data.append({
                "id": r.id,
                "rider": r.rider.phone,
                "driver": r.driver.user.phone if r.driver else None,
                "status": r.status,
                "pickup": r.pickup_lat, # simplify for list
                "created_at": r.created_at,
                "fare": r.final_fare,
            })
        return Response(data)

class AdminRideActionView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request):
        ride_id = request.data.get("ride_id")
        action = request.data.get("action")
        
        if action != "cancel":
            return Response({"error": "Invalid action"}, status=400)
            
        try:
            ride = Ride.objects.get(id=ride_id)
            ride.cancel(by="SYSTEM") # or ADMIN
            return Response({"success": True, "status": ride.status})
        except Ride.DoesNotExist:
             return Response({"error": "Ride not found"}, status=404)
