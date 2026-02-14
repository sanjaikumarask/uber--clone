from django.urls import re_path
from apps.tracking.consumers.driver_location import DriverLocationConsumer
from apps.tracking.consumers.admin_live_map import AdminLiveMapConsumer

websocket_urlpatterns = [
    re_path(
        r"ws/driver/location/$",
        DriverLocationConsumer.as_asgi(),
    ),
    re_path(
        r"ws/admin/live-map/$",
        AdminLiveMapConsumer.as_asgi(),
    ),
]
