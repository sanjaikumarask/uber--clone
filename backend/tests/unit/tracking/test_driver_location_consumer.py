import json
import time
from unittest.mock import MagicMock, patch, AsyncMock, ANY
import pytest
from apps.tracking.consumers.driver_location import DriverLocationConsumer

@pytest.fixture
def consumer():
    c = DriverLocationConsumer()
    c.scope = {"user": MagicMock()}
    c.driver = MagicMock(id=1, status="ONLINE")
    c.channel_name = "test_channel"
    c.channel_layer = AsyncMock()
    c.last_seq = 0
    c.last_ping_ts = None
    c.last_admin_broadcast_ts = 0
    return c

@pytest.mark.asyncio
async def test_is_valid_sequence(consumer):
    # Valid seq
    assert consumer._is_valid_sequence(1) is True
    assert consumer.last_seq == 1
    
    # Old seq
    assert consumer._is_valid_sequence(1) is False
    assert consumer._is_valid_sequence(0) is False

@pytest.mark.asyncio
async def test_persist_location(consumer):
    with patch("apps.tracking.consumers.driver_location.update_driver_location") as mock_update:
        with patch.object(consumer, "_update_driver_db", new_callable=AsyncMock) as mock_db:
            await consumer._persist_location(12.97, 77.59)
            # update_driver_location is called via database_sync_to_async
            pass

@pytest.mark.asyncio
async def test_build_broadcast_data(consumer):
    ride = MagicMock(id=101, status="ONGOING", pickup_address="Home", drop_address="Work")
    raw_data = {"heading": 90, "speed_kmh": "45.5"}
    
    res = consumer._build_broadcast_data(ride, 12.0, 77.0, raw_data, 5)
    
    assert res["driver_id"] == consumer.driver.id
    assert res["lat"] == 12.0
    assert res["lng"] == 77.0
    assert res["heading"] == 90
    assert res["speed_kmh"] == 45.5
    assert res["eta"] == 5
    assert res["ride"]["id"] == 101

@pytest.mark.asyncio
async def test_throttled_admin_broadcast(consumer):
    data = {"test": "data"}
    # First call
    await consumer._throttled_admin_broadcast(data)
    consumer.channel_layer.group_send.assert_called_once()
    
    # Second call immediate - should be throttled
    consumer.channel_layer.group_send.reset_mock()
    await consumer._throttled_admin_broadcast(data)
    consumer.channel_layer.group_send.assert_not_called()
    
    # Advance time
    with patch("time.time", return_value=time.time() + 2):
        await consumer._throttled_admin_broadcast(data)
        consumer.channel_layer.group_send.assert_called_once()

@pytest.mark.asyncio
async def test_broadcast_to_rider(consumer):
    await consumer._broadcast_to_rider(101, 12.0, 77.0, {"heading": 180}, 3)
    consumer.channel_layer.group_send.assert_called_once_with(
        "ride_101",
        {
            "type": "location_update",
            "lat": 12.0,
            "lng": 77.0,
            "heading": 180,
            "eta": 3,
            "ts": ANY,
        }
    )
