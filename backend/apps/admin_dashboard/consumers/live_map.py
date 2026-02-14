from channels.generic.websocket import AsyncJsonWebsocketConsumer


class AdminLiveMapConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")

        if not user or not user.is_authenticated or not user.is_admin:
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(
            "admin_live_map",
            self.channel_name,
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            "admin_live_map",
            self.channel_name,
        )

    async def driver_location_update(self, event):
        await self.send_json(event["data"])
