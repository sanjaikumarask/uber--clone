from django.urls import re_path
from apps.tracking.consumers.rider_tracking import RiderTrackingConsumer

websocket_urlpatterns = [
    re_path(
        r"ws/rides/(?P<ride_id>\d+)/$",
        RiderTrackingConsumer.as_asgi(),
    ),
]
