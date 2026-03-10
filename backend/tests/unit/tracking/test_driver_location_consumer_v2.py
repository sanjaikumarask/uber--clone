import pytest
import json
import time
from unittest.mock import patch
from channels.testing import WebsocketCommunicator
from channels.db import database_sync_to_async
from config.asgi import application
from apps.drivers.models import Driver
from apps.rides.models import Ride
from rest_framework_simplejwt.tokens import AccessToken
import apps.tracking.consumers.driver_location

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
class TestDriverLocationConsumerV2:
    
    async def test_driver_location_lifecycle(self, driver_user):
        # Ensure driver is offline initially
        driver = driver_user.driver
        
        def _set_offline():
            driver.status = Driver.Status.OFFLINE
            driver.save()
        await database_sync_to_async(_set_offline)()
        
        # 1. Generate JWT Token
        token = await database_sync_to_async(AccessToken.for_user)(driver_user)
        
        # 2. Connect via WebSocket
        communicator = WebsocketCommunicator(
            application, 
            f"/ws/tracking/driver-location/?token={token}"
        )
        connected, subprotocol = await communicator.connect()
        assert connected
        
        # Verify driver is automatically moved to ONLINE status
        await database_sync_to_async(driver.refresh_from_db)()
        assert driver.status == Driver.Status.ONLINE
        
        # 3. Test Ping/Pong
        await communicator.send_json_to({"type": "ping"})
        response = await communicator.receive_json_from()
        assert response["type"] == "pong"
        assert "ts" in response
        
        # 4. Test Location Update (Happy Path)
        location_data = {
            "type": "location",
            "lat": 12.9716,
            "lng": 77.5946,
            "seq": 1,
            "accuracy_m": 5,
            "speed_kmh": 35.5,
            "heading": 120
        }
        await communicator.send_json_to(location_data)
        
        # Expect location_sync response
        response = await communicator.receive_json_from()
        assert response["type"] == "location_sync"
        assert response["lat"] == 12.9716
        assert response["lng"] == 77.5946
        
        # 6. Test Disconnect
        await communicator.disconnect()

    async def test_location_with_active_ride(self, driver_user, ride):
        # Setup: Assigned ride
        driver = driver_user.driver

        def _setup_ride():
            ride.driver = driver
            ride.status = Ride.Status.ASSIGNED
            ride.save()
        await database_sync_to_async(_setup_ride)()

        token = await database_sync_to_async(AccessToken.for_user)(driver_user)
        communicator = WebsocketCommunicator(application, f"/ws/tracking/driver-location/?token={token}")
        await communicator.connect()

        # Use seq=1 (not a multiple of 10) to avoid triggering the
        # snap_to_roads Google Maps API call (only fires when seq % 10 == 0),
        # which would make an external HTTP request and timeout in tests.
        with patch("apps.tracking.services.snap_to_roads"):
            await communicator.send_json_to({
                "type": "location",
                "lat": 12.9716,
                "lng": 77.5946,
                "seq": 1,
            })
            response = await communicator.receive_json_from()
        assert response["type"] == "location_sync"

        await communicator.disconnect()
