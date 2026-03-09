import pytest
import json
from unittest.mock import patch, MagicMock
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from apps.tracking.consumers.driver_location import DriverLocationConsumer
from django.contrib.auth import get_user_model
from apps.drivers.models import Driver

User = get_user_model()


@database_sync_to_async
def create_user(username, role="driver"):
    return User.objects.create_user(username=username, role=role)


@database_sync_to_async
def create_driver(user, status="ONLINE"):
    d, _ = Driver.objects.get_or_create(user=user)
    d.status = status
    d.is_verified = True
    d.save()
    return d


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestDriverLocationConsumerFull:

    async def test_unauthenticated_connection_rejected(self):
        """Trigger lines 50-53: unauthenticated user is closed with code 4001."""
        communicator = WebsocketCommunicator(
            DriverLocationConsumer.as_asgi(), "/ws/tracking/driver/"
        )
        communicator.scope["user"] = None

        connected, subprotocol = await communicator.connect()
        assert not connected
        assert subprotocol == 4001

    async def test_no_driver_profile_rejected(self):
        """Trigger lines 55-58: user with no driver profile is closed with code 4003."""
        non_driver_user = await create_user("no_profile_user_dlf_v2", role="rider")
        communicator = WebsocketCommunicator(
            DriverLocationConsumer.as_asgi(), "/ws/tracking/driver/"
        )
        communicator.scope["user"] = non_driver_user

        connected, subprotocol = await communicator.connect()
        assert not connected
        assert subprotocol == 4003

    async def test_driver_connect_and_disconnect(self):
        """Trigger lines 44-47, 238-266: connect + disconnect lifecycle."""
        user = await create_user("dlf_connect_driver_v2")
        await create_driver(user)

        communicator = WebsocketCommunicator(
            DriverLocationConsumer.as_asgi(), "/ws/tracking/driver/"
        )
        communicator.scope["user"] = user

        connected, _ = await communicator.connect()
        assert connected

        await communicator.disconnect()

    @patch("apps.tracking.consumers.driver_location.update_driver_location")
    @patch("apps.tracking.consumers.driver_location.get_driver_last_point")
    @patch("apps.tracking.consumers.driver_location.set_driver_last_point")
    async def test_ping_returns_pong(self, mock_set_last, mock_get_last, mock_update):
        """Trigger lines 95-97: ping message returns pong immediately."""
        user = await create_user("dlf_ping_driver_v2")
        await create_driver(user)

        communicator = WebsocketCommunicator(
            DriverLocationConsumer.as_asgi(), "/ws/tracking/driver/"
        )
        communicator.scope["user"] = user
        connected, _ = await communicator.connect()
        assert connected

        await communicator.send_json_to({"type": "ping"})
        response = await communicator.receive_json_from()
        assert response["type"] == "pong"

        await communicator.disconnect()

    @patch("apps.tracking.consumers.driver_location.update_driver_location")
    @patch("apps.tracking.services.LocationProcessor.get_snapped_coords")
    async def test_sequence_deduplication_drops_old_seq(self, mock_snapped, mock_update):
        """Trigger lines 99-100: stale sequence number is silently dropped."""
        mock_snapped.return_value = (13.0, 80.0)
        
        user = await create_user("dlf_seq_driver_v2")
        await create_driver(user)

        communicator = WebsocketCommunicator(
            DriverLocationConsumer.as_asgi(), "/ws/tracking/driver/"
        )
        communicator.scope["user"] = user
        connected, _ = await communicator.connect()
        assert connected

        # Send a valid update first
        await communicator.send_json_to(
            {"type": "location_update", "seq": 10, "lat": 13.0, "lng": 80.0}
        )
        # It should send location_sync back
        await communicator.receive_json_from()

        # Now send a lower seq — it should be dropped (no response)
        await communicator.send_json_to(
            {"type": "location_update", "seq": 3, "lat": 13.0, "lng": 80.0}
        )
        # receive_nothing returns True if no message arrives within timeout
        assert await communicator.receive_nothing(timeout=0.5)

        await communicator.disconnect()

    @patch("apps.tracking.consumers.driver_location.update_driver_location")
    @patch("apps.tracking.consumers.driver_location.get_driver_last_point")
    @patch("apps.tracking.consumers.driver_location.set_driver_last_point")
    @patch("apps.tracking.services.LocationProcessor.get_snapped_coords")
    async def test_location_sync_response(self, mock_snapped, mock_set, mock_get, mock_update):
        """Trigger lines 110-117: valid location update returns location_sync."""
        mock_get.return_value = (13.0, 80.0)
        mock_snapped.return_value = (13.1, 80.1)

        user = await create_user("dlf_loc_driver_v2")
        await create_driver(user)

        communicator = WebsocketCommunicator(
            DriverLocationConsumer.as_asgi(), "/ws/tracking/driver/"
        )
        communicator.scope["user"] = user
        await communicator.connect()

        await communicator.send_json_to(
            {"type": "location_update", "seq": 1, "lat": 13.1, "lng": 80.1, "accuracy_m": 5}
        )
        response = await communicator.receive_json_from()
        assert response["type"] == "location_sync"
        assert response["lat"] == 13.1

        await communicator.disconnect()

    @patch("apps.tracking.consumers.driver_location.update_driver_location")
    @patch("apps.tracking.services.LocationProcessor.get_snapped_coords")
    @patch("apps.tracking.services.LocationProcessor.filter_noisy_ping")
    async def test_noisy_ping_skipped(self, mock_noisy, mock_snapped, mock_update):
        """Trigger lines 106-108: noisy pings are filtered."""
        mock_noisy.return_value = True
        user = await create_user("dlf_noisy_v2")
        await create_driver(user)
        communicator = WebsocketCommunicator(DriverLocationConsumer.as_asgi(), "/ws/tracking/driver/")
        communicator.scope["user"] = user
        await communicator.connect()
        # Mock accuracy_m to trigger noisy ping filter
        await communicator.send_json_to({"type": "location_update", "seq": 1, "lat": 13, "lng": 80, "accuracy_m": 500})
        # location_sync won't be sent because early return
        assert await communicator.receive_nothing()
        mock_update.assert_called()
        await communicator.disconnect()

    @patch("apps.tracking.consumers.driver_location.update_driver_location")
    @patch("apps.tracking.services.LocationProcessor.get_snapped_coords")
    async def test_route_deviation_alert(self, mock_snapped, mock_update):
        """Trigger lines 131-150, 168-182: route deviation logic."""
        mock_snapped.return_value = (13.1, 80.1)
        mock_update.return_value = None
        user = await create_user("dlf_dev_v2")
        driver = await create_driver(user)
        
        from apps.rides.models import Ride
        @database_sync_to_async
        def create_active_ride():
            return Ride.objects.create(
                rider=user, driver=driver, status=Ride.Status.ONGOING,
                pickup_lat=13.0, pickup_lng=80.0, drop_lat=13.5, drop_lng=80.5,
                planned_route_polyline="encoded_polyline"
            )
        ride = await create_active_ride()

        communicator = WebsocketCommunicator(DriverLocationConsumer.as_asgi(), "/ws/tracking/driver/")
        communicator.scope["user"] = user
        await communicator.connect()

        # Re-mock to return high deviation
        with patch("apps.tracking.consumers.driver_location.snap_to_route", return_value=((13.1, 80.1), 500.0)), \
             patch("apps.tracking.consumers.driver_location.is_deviated", return_value=True), \
             patch("apps.tracking.consumers.driver_location.decode_route", return_value=[]):
            await communicator.send_json_to({"type": "location_update", "seq": 1, "lat": 13.1, "lng": 80.1})
            await communicator.receive_json_from() # location_sync

        await communicator.disconnect()

    async def test_force_disconnect(self):
        """Trigger lines 225-236: session eviction by connecting a second time."""
        user = await create_user("dlf_evict_v2")
        await create_driver(user)
        
        # First connection
        comm1 = WebsocketCommunicator(DriverLocationConsumer.as_asgi(), "/ws/tracking/driver/")
        comm1.scope["user"] = user
        connected1, _ = await comm1.connect()
        assert connected1
        
        # Second connection for the same driver
        comm2 = WebsocketCommunicator(DriverLocationConsumer.as_asgi(), "/ws/tracking/driver/")
        comm2.scope["user"] = user
        connected2, _ = await comm2.connect()
        assert connected2
        
        # The first connection should receive the error and close
        response = await comm1.receive_json_from()
        assert response["type"] == "error"
        assert response["code"] == "SESSION_EVICTED"
        
        await comm1.disconnect()
        await comm2.disconnect()
