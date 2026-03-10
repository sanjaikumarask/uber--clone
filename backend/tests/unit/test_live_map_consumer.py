import json
import pytest
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from apps.admin_dashboard.consumers.live_map import AdminLiveMapConsumer
from apps.drivers.models import Driver
from apps.rides.models import Ride
from asgiref.sync import sync_to_async

User = get_user_model()

@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestAdminLiveMapConsumer:
    """
    Test suite for AdminLiveMapConsumer (ws/admin/live-map/).
    Focuses on connection auth, initial snapshotting, and event forwarding.
    """

    @pytest.fixture
    async def admin_user(self):
        # Set role="admin" specifically so save() logic doesn't strip superuser/staff bits
        user = await sync_to_async(User.objects.create_superuser)(
            username="admin_test", 
            phone="+919999999999", 
            password="adminpassword",
            role=User.ROLE_ADMIN
        )
        return user

    @pytest.fixture
    async def regular_user(self):
        user = await sync_to_async(User.objects.create_user)(
            username="regular_test", phone="+918888888888", password="userpassword"
        )
        return user

    async def test_connect_unauthenticated_rejected(self):
        communicator = WebsocketCommunicator(AdminLiveMapConsumer.as_asgi(), "ws/admin/live-map/")
        # Mock scope to simulate no user
        communicator.scope["user"] = None
        connected, subprotocol = await communicator.connect()
        assert not connected
        assert subprotocol == 4001
        await communicator.disconnect()

    async def test_connect_regular_user_rejected(self, regular_user):
        communicator = WebsocketCommunicator(AdminLiveMapConsumer.as_asgi(), "ws/admin/live-map/")
        communicator.scope["user"] = regular_user
        connected, subprotocol = await communicator.connect()
        assert not connected
        assert subprotocol == 4003
        await communicator.disconnect()

    async def test_connect_admin_user_accepted(self, admin_user):
        communicator = WebsocketCommunicator(AdminLiveMapConsumer.as_asgi(), "ws/admin/live-map/")
        communicator.scope["user"] = admin_user
        connected, _ = await communicator.connect()
        assert connected
        await communicator.disconnect()

    async def test_initial_snapshot_with_drivers(self, admin_user):
        # Setup: Create a driver and its location data
        driver_user = await sync_to_async(User.objects.create_user)(
            username="driver_test", phone="+917777777777", password="driverpassword"
        )
        driver = await sync_to_async(Driver.objects.create)(
            user=driver_user, status="ONLINE", last_lat=12.9716, last_lng=77.5946
        )

        communicator = WebsocketCommunicator(AdminLiveMapConsumer.as_asgi(), "ws/admin/live-map/")
        communicator.scope["user"] = admin_user
        connected, _ = await communicator.connect()
        assert connected

        # Test receive snapshot
        response = await communicator.receive_json_from()
        assert response["type"] == "DRIVER_LOCATION_UPDATED"
        assert response["data"]["driver_id"] == driver.id
        assert response["data"]["lat"] == 12.9716

        await communicator.disconnect()

    async def test_driver_location_update_forwarding(self, admin_user):
        from unittest.mock import AsyncMock
        
        # Instantiate consumer directly for handler tests
        consumer = AdminLiveMapConsumer()
        consumer.scope = {"user": admin_user}
        consumer.send = AsyncMock()
        
        # Trigger forwarding event
        event = {
            "type": "driver_location_updated",
            "data": {
                "driver_id": 123,
                "lat": 13.0,
                "lng": 78.0
            }
        }
        await consumer.driver_location_updated(event)
        
        # Verify call
        args, kwargs = consumer.send.call_args
        sent_data = json.loads(kwargs["text_data"])
        assert sent_data["type"] == "DRIVER_LOCATION_UPDATED"
        assert sent_data["data"]["driver_id"] == 123

    async def test_admin_generic_event_forwarding(self, admin_user):
        from unittest.mock import AsyncMock
        
        consumer = AdminLiveMapConsumer()
        consumer.scope = {"user": admin_user}
        consumer.send = AsyncMock()

        event = {
            "type": "admin_generic_event",
            "event": "RIDE_CANCELLED",
            "data": {"ride_id": 47}
        }
        await consumer.admin_generic_event(event)

        args, kwargs = consumer.send.call_args
        sent_data = json.loads(kwargs["text_data"])
        assert sent_data["type"] == "RIDE_CANCELLED"
        assert sent_data["data"]["ride_id"] == 47

    async def test_route_deviation_alert_forwarding(self, admin_user):
        from unittest.mock import AsyncMock
        
        consumer = AdminLiveMapConsumer()
        consumer.scope = {"user": admin_user}
        consumer.send = AsyncMock()

        event = {
            "type": "route_deviation_alert",
            "data": {
                "driver_id": 1,
                "ride_id": 47,
                "deviation_m": 500
            }
        }
        await consumer.route_deviation_alert(event)

        args, kwargs = consumer.send.call_args
        sent_data = json.loads(kwargs["text_data"])
        assert sent_data["type"] == "ROUTE_DEVIATION"
        assert sent_data["data"]["deviation_m"] == 500

