# apps/tracking/routing.py

from django.urls import re_path

from apps.admin_dashboard.consumers.live_map import AdminLiveMapConsumer
from apps.tracking.consumers.driver_location import DriverLocationConsumer
from apps.tracking.consumers.driver_rides import DriverRidesConsumer

websocket_urlpatterns = [
    # Driver sends GPS pings here → DriverLocationConsumer processes &
    # broadcasts to the rider's ride_ channel group
    re_path(
        r"ws/tracking/driver-location/$",
        DriverLocationConsumer.as_asgi(),
    ),
    # Driver receives ride offers here → DriverRidesConsumer forwards
    # any ride_offer group_send events to the connected driver
    # BUG FIX: Added trailing slash to match incoming request URL
    re_path(
        r"ws/tracking/driver-rides/$",
        DriverRidesConsumer.as_asgi(),
    ),
    # Admin live map — receives all driver location broadcasts
    re_path(
        r"ws/admin/live-map/$",
        AdminLiveMapConsumer.as_asgi(),
    ),
]
