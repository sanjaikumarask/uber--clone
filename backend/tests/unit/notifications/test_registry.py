import pytest
from apps.notifications.services.registry import default_builder, EVENT_REGISTRY

class TestNotificationRegistry:
    def test_default_builder_valid_input(self):
        data = {"key": "value"}
        result = default_builder(data)
        assert result == data
        
    def test_default_builder_invalid_input(self):
        result = default_builder(None)
        assert result is None
        
    def test_registry_contains_expected_keys(self):
        expected_keys = [
            "DRIVER_RIDE_OFFER",
            "RIDE_ASSIGNED",
            "RIDE_STARTED",
            "RIDE_COMPLETED",
            "RIDE_CANCELLED"
        ]
        assert all(key in EVENT_REGISTRY for key in expected_keys)
        
    def test_registry_structure(self):
        for key, value in EVENT_REGISTRY.items():
            assert "channels" in value
            assert isinstance(value["channels"], list)
            assert "payload_builder" in value
            assert callable(value["payload_builder"])
