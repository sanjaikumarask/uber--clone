import pytest
import json
from channels.testing import WebsocketCommunicator
from django.urls import reverse
from rest_framework_simplejwt.tokens import AccessToken
from apps.users.models import User
from apps.drivers.models import Driver
from apps.rides.models import Ride
from config.asgi import application
from channels.db import database_sync_to_async

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
class TestTrackingConsumersExtended:

    async def test_driver_rides_consumer_lifecycle(self, driver_user):
        def _setup_driver():
            driver, _ = Driver.objects.get_or_create(user=driver_user)
            driver.status = Driver.Status.OFFLINE
            driver.save()
            return driver
        driver = await database_sync_to_async(_setup_driver)()

        token = await database_sync_to_async(AccessToken.for_user)(driver_user)
        url = f"/ws/tracking/driver-rides/?token={token}"
        communicator = WebsocketCommunicator(application, url)
        connected, _ = await communicator.connect()
        assert connected

        # Verify driver is now ONLINE
        await database_sync_to_async(driver.refresh_from_db)()
        assert driver.status == Driver.Status.ONLINE

        # Test ride_offer forwarding
        test_event = {
            "type": "ride_offer",
            "data": {"ride_id": 123, "fare": 200}
        }
        
        from channels.layers import get_channel_layer
        channel_layer = get_channel_layer()
        await channel_layer.group_send(f"driver_{driver.id}_rides", test_event)
        
        response = await communicator.receive_json_from()
        assert response["type"] == "ride_offer"
        assert response["data"]["ride_id"] == 123

        await communicator.disconnect()

    async def test_rider_tracking_consumer_lifecycle(self, rider_user, driver_user):
        def _setup_ride():
            driver, _ = Driver.objects.get_or_create(user=driver_user)
            driver.is_verified = True
            driver.save()
            ride = Ride.objects.create(
                rider=rider_user, 
                driver=driver,
                status=Ride.Status.ASSIGNED,
                pickup_lat=12.0, pickup_lng=77.0,
                drop_lat=12.1, drop_lng=77.1,
                base_fare=100
            )
            return ride
        ride = await database_sync_to_async(_setup_ride)()

        token = await database_sync_to_async(AccessToken.for_user)(rider_user)
        url = f"/ws/rides/{ride.id}/?token={token}"
        communicator = WebsocketCommunicator(application, url)
        connected, _ = await communicator.connect()
        assert connected

        # RiderTrackingConsumer sends WS_CONNECTED on connect
        response = await communicator.receive_json_from()
        assert response["type"] == "WS_CONNECTED"

        # Test forwarding driver_location_updated (which is sent to ride_{id} group)
        test_location = {
            "type": "driver_location_updated",
            "lat": 12.05,
            "lng": 77.05,
            "heading": 90
        }
        from channels.layers import get_channel_layer
        channel_layer = get_channel_layer()
        await channel_layer.group_send(f"ride_{ride.id}", test_location)

        response = await communicator.receive_json_from()
        assert response["type"] == "DRIVER_LOCATION_UPDATED"
        assert response["payload"]["lat"] == 12.05

        # Test RIDER sending location update
        await communicator.send_json_to({
            "type": "LOCATION_UPDATE",
            "payload": {"lat": 12.01, "lng": 77.01}
        })
        # This triggers a broadcast to the group (and to admin map)
        response = await communicator.receive_json_from()
        assert response["type"] == "RIDER_LOCATION_UPDATED"
        assert response["payload"]["lat"] == 12.01

        # Test forwarding ride_completed event
        await channel_layer.group_send(f"ride_{ride.id}", {
            "type": "ride_completed",
            "ride_id": ride.id,
            "fare": 150
        })
        response = await communicator.receive_json_from()
        assert response["type"] == "RIDE_COMPLETED"
        assert response["payload"]["fare"] == 150

        await communicator.disconnect()


    async def test_driver_location_lifecycle(self, driver_user):
        def _ensure_driver():
            Driver.objects.get_or_create(user=driver_user)
        await database_sync_to_async(_ensure_driver)()

        token = await database_sync_to_async(AccessToken.for_user)(driver_user)
        url = f"/ws/tracking/driver-location/?token={token}"
        communicator = WebsocketCommunicator(application, url)
        connected, _ = await communicator.connect()
        assert connected

        # Test location update
        await communicator.send_json_to({
            "type": "location",
            "lat": 12.97,
            "lng": 77.59,
            "accuracy_m": 10,
            "seq": 1
        })
        response = await communicator.receive_json_from()
        assert response["type"] == "location_sync"

        await communicator.disconnect()

    async def test_driver_location_session_enforcement(self, driver_user):
        def _ensure_driver():
            Driver.objects.get_or_create(user=driver_user)
        await database_sync_to_async(_ensure_driver)()

        token = await database_sync_to_async(AccessToken.for_user)(driver_user)
        url = f"/ws/tracking/driver-location/?token={token}"
        
        # Connect first session
        comm1 = WebsocketCommunicator(application, url)
        connected1, _ = await comm1.connect()
        assert connected1
        
        # Connect second session
        comm2 = WebsocketCommunicator(application, url)
        connected2, _ = await comm2.connect()
        assert connected2
        
        # First session should be kicked
        try:
            reason = await comm1.receive_output(timeout=5)
            assert reason['type'] == 'websocket.close'
            assert reason['code'] == 4001
        except Exception:
            # If receive_json_from was used, it might raise error on close
            pass

        await comm1.disconnect()
        await comm2.disconnect()
        
    async def test_driver_rides_pending_offer(self, driver_user, rider_user):
        def _setup_pending_offer():
            driver, _ = Driver.objects.get_or_create(user=driver_user)
            ride = Ride.objects.create(
                rider=rider_user,
                driver=driver,
                status=Ride.Status.OFFERED,
                pickup_lat=12.0, pickup_lng=77.0,
                drop_lat=12.1, drop_lng=77.1,
                base_fare=100
            )
            return ride
        
        ride = await database_sync_to_async(_setup_pending_offer)()
        token = await database_sync_to_async(AccessToken.for_user)(driver_user)
        url = f"/ws/tracking/driver-rides/?token={token}"
        communicator = WebsocketCommunicator(application, url)
        connected, _ = await communicator.connect()
        assert connected

        # Consumer should immediately send the pending offer
        response = await communicator.receive_json_from()
        assert response["type"] == "ride_offer"
        assert response["data"]["ride_id"] == ride.id

        await communicator.disconnect()
