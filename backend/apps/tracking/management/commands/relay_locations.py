import json

import redis
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        r = redis.from_url(settings.REDIS_URL)
        pubsub = r.pubsub()
        pubsub.psubscribe("ride:*:location")

        channel_layer = get_channel_layer()

        for message in pubsub.listen():
            if message["type"] != "pmessage":
                continue

            channel = message["channel"].decode()
            ride_id = channel.split(":")[1]
            data = json.loads(message["data"])

            async_to_sync(channel_layer.group_send)(
                f"ride_{ride_id}",
                {
                    "type": "location.update",
                    "data": data,
                },
            )
