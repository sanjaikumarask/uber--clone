from channels.generic.websocket import AsyncJsonWebsocketConsumer


class DriverIncentiveConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.group_name = "driver_incentives"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def incentive_update(self, event):
        await self.send_json(event["content"])
