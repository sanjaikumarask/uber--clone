from django.urls import re_path
from apps.rides.consumers import RideConsumer

websocket_urlpatterns = [
    re_path(
        r"ws/rides/(?P<ride_id>\d+)/$",
        RideConsumer.as_asgi(),
    ),
]
