import pytest
import json
import time
from unittest.mock import patch, MagicMock, AsyncMock
from channels.testing import WebsocketCommunicator
from channels.db import database_sync_to_async
from config.asgi import application
from apps.drivers.models import Driver
from apps.rides.models import Ride
from rest_framework_simplejwt.tokens import AccessToken

@pytest.fixture(autouse=True)
def mock_tracking_services():
    with patch("apps.tracking.services.LocationProcessor.get_snapped_coords", new_callable=AsyncMock) as mock_snap, \
         patch("apps.tracking.consumers.driver_location.decode_route") as mock_decode:
        mock_snap.return_value = (12.0, 77.0)
        mock_decode.return_value = [(12.0, 77.0)]
        yield mock_snap, mock_decode

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
class TestDriverLocationConsumerFinal:
    
    async def setup_driver(self, driver_user):
        driver = driver_user.driver
        def _sync_setup():
            driver.status = Driver.Status.OFFLINE
            driver.last_lat = 12.0
            driver.last_lng = 77.0
            driver.save()
        await database_sync_to_async(_sync_setup)()
        token = await database_sync_to_async(AccessToken.for_user)(driver_user)
        return driver, token

    async def test_full_lifecycle_and_ping(self, driver_user):
        driver, token = await self.setup_driver(driver_user)
        communicator = WebsocketCommunicator(application, f"/ws/tracking/driver-location/?token={token}")
        with patch("apps.common.backpressure.ConnectionRateLimiter.is_allowed", return_value=True):
            connected, _ = await communicator.connect()
            assert connected
        await database_sync_to_async(driver.refresh_from_db)()
        assert driver.status == Driver.Status.ONLINE
        await communicator.send_json_to({"type": "ping"})
        response = await communicator.receive_json_from()
        assert response["type"] == "pong"
        await communicator.disconnect()

    async def test_authentication_failures(self, driver_user):
        communicator = WebsocketCommunicator(application, "/ws/tracking/driver-location/")
        connected, _ = await communicator.connect()
        assert not connected
        from apps.users.models import User
        def _create_user():
             u = User.objects.create_user(username="no_driver_final", phone="0004")
             return u, AccessToken.for_user(u)
        user_no_dr, token_no_dr = await database_sync_to_async(_create_user)()
        comm = WebsocketCommunicator(application, f"/ws/tracking/driver-location/?token={token_no_dr}")
        connected, _ = await comm.connect()
        assert not connected

    async def test_rate_limiting(self, driver_user):
        driver, token = await self.setup_driver(driver_user)
        communicator = WebsocketCommunicator(application, f"/ws/tracking/driver-location/?token={token}")
        with patch("apps.common.backpressure.ConnectionRateLimiter.is_allowed", return_value=False):
            connected, _ = await communicator.connect()
            assert not connected

    async def test_session_eviction(self, driver_user):
        driver, token = await self.setup_driver(driver_user)
        comm1 = WebsocketCommunicator(application, f"/ws/tracking/driver-location/?token={token}")
        await comm1.connect()
        comm2 = WebsocketCommunicator(application, f"/ws/tracking/driver-location/?token={token}")
        await comm2.connect()
        response = await comm1.receive_json_from()
        assert response["type"] == "error"
        assert response["code"] == "SESSION_EVICTED"
        await comm1.disconnect()
        await comm2.disconnect()

    async def test_location_logic_branches(self, driver_user, ride):
        driver, token = await self.setup_driver(driver_user)
        def _setup_ride():
            ride.driver = driver
            ride.status = Ride.Status.ONGOING
            ride.save()
        await database_sync_to_async(_setup_ride)()

        communicator = WebsocketCommunicator(application, f"/ws/tracking/driver-location/?token={token}")
        await communicator.connect()

        # 1. Invalid sequence (seq is None)
        await communicator.send_json_to({"type": "location", "lat": 12.0, "lng": 77.0, "seq": None})
        assert await communicator.receive_nothing(timeout=0.2) is True

        # 2. Invalid sequence (repeated)
        # Seed a seq first
        await communicator.send_json_to({"type": "location", "lat": 12.0, "lng": 77.0, "seq": 10})
        await communicator.receive_json_from()
        
        await communicator.send_json_to({"type": "location", "lat": 12.0, "lng": 77.0, "seq": 10})
        assert await communicator.receive_nothing(timeout=0.2) is True

        # 3. Noisy Ping
        await communicator.send_json_to({"type": "location", "lat": 12.0, "lng": 77.0, "seq": 15, "accuracy_m": 150})
        assert await communicator.receive_nothing(timeout=0.2) is True

        # 4. Throttled alert branch
        current_time = [200.0]
        def mock_time():
            current_time[0] += 1.0
            return current_time[0]

        with patch("apps.tracking.consumers.driver_location.snap_to_route", return_value=((10.0, 70.0), 1000.0)), \
             patch("apps.tracking.consumers.driver_location.is_deviated", return_value=True), \
             patch("apps.tracking.consumers.driver_location.time.time", side_effect=mock_time):
            
            await communicator.send_json_to({"type": "location", "lat": 12.0, "lng": 77.0, "seq": 20})
            await communicator.receive_json_from()
            
            # Second alert inside 30s
            await communicator.send_json_to({"type": "location", "lat": 12.1, "lng": 77.1, "seq": 21})
            await communicator.receive_json_from()

        await communicator.disconnect()

    async def test_disconnect_cleanup(self, driver_user):
        driver, token = await self.setup_driver(driver_user)
        communicator = WebsocketCommunicator(application, f"/ws/tracking/driver-location/?token={token}")
        await communicator.connect()
        
        from apps.drivers.redis import redis_client
        
        class MatchAnything:
            def __eq__(self, other):
                return True
        
        with patch.object(redis_client, 'get', return_value=MatchAnything()), \
             patch.object(redis_client, 'delete') as mock_delete:
            await communicator.disconnect()
            assert mock_delete.called

    async def test_disconnect_no_prev_location(self, driver_user):
        driver, token = await self.setup_driver(driver_user)
        def _clear():
            driver.last_lat = None
            driver.save()
        await database_sync_to_async(_clear)()
        
        comm = WebsocketCommunicator(application, f"/ws/tracking/driver-location/?token={token}")
        await comm.connect()
        await comm.disconnect()

    async def test_exception_handling_in_get_driver(self, driver_user):
        token = await database_sync_to_async(AccessToken.for_user)(driver_user)
        with patch("apps.drivers.models.Driver.objects.select_related", side_effect=Exception("DB FAIL")):
            communicator = WebsocketCommunicator(application, f"/ws/tracking/driver-location/?token={token}")
            connected, _ = await communicator.connect()
            assert not connected
