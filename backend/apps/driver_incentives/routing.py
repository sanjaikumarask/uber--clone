from django.urls import path

from . import consumers

websocket_urlpatterns = [
    path("ws/driver-incentives/", consumers.DriverIncentiveConsumer.as_asgi()),
]
