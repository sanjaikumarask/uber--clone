from django.urls import re_path
from .consumers.live_map import AdminLiveMapConsumer

websocket_urlpatterns = [
    re_path(r"ws/admin/live-map/$", AdminLiveMapConsumer.as_asgi()),
]
