import pytest
from apps.notifications.services.payloads import (
    ride_assigned_payload,
    ride_started_payload,
    ride_completed_payload
)

class TestNotificationPayloads:
    def test_ride_assigned_payload_valid(self):
        data = {"driver_name": "John Doe", "ride_id": 1, "vehicle": "Toyota Prius"}
        payload = ride_assigned_payload(data)
        assert payload["title"] == "Driver Assigned"
        assert "John Doe" in payload["body"]
        assert payload["ride_id"] == 1
        assert payload["vehicle"] == "Toyota Prius"

    def test_ride_assigned_payload_invalid(self):
        with pytest.raises(KeyError):
            ride_assigned_payload({"ride_id": 1})

    def test_ride_started_payload_valid(self):
        data = {"ride_id": 1}
        payload = ride_started_payload(data)
        assert payload["title"] == "Ride Started"
        assert payload["ride_id"] == 1
        
    def test_ride_started_payload_invalid(self):
        with pytest.raises(KeyError):
            ride_started_payload({})

    def test_ride_completed_payload_valid(self):
        data = {"ride_id": 1, "fare": 15.5}
        payload = ride_completed_payload(data)
        assert payload["title"] == "Ride Completed"
        assert payload["ride_id"] == 1
        assert payload["fare"] == 15.5
        
    def test_ride_completed_payload_missing_optional(self):
        data = {"ride_id": 1}
        payload = ride_completed_payload(data)
        assert payload["fare"] is None
