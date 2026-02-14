import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer

from apps.drivers.redis import redis_client

DRIVER_GEO_KEY = "drivers:live"


class AdminLiveMapConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope["user"]

        if not user.is_authenticated or not user.is_admin:
            await self.close(code=4003)
            return

        await self.accept()
        self.running = True
        self.task = asyncio.create_task(self.stream_locations())

    async def disconnect(self, code):
        self.running = False
        if hasattr(self, "task"):
            self.task.cancel()

    async def stream_locations(self):
        while self.running:
            drivers = redis_client.zrange(DRIVER_GEO_KEY, 0, -1)
            payload = []

            for driver_id in drivers:
                key = f"driver:{driver_id.decode()}:meta"
                data = redis_client.hgetall(key)

                if not data:
                    continue

                payload.append({
                    "driver_id": int(driver_id),
                    "lat": float(data[b"lat"]),
                    "lng": float(data[b"lng"]),
                    "status": data[b"status"].decode(),
                })

            await self.send(text_data=json.dumps({
                "type": "DRIVER_LOCATIONS",
                "drivers": payload,
            }))

            await asyncio.sleep(1)
