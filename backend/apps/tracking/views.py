from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from apps.users.permissions import IsDriver

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
