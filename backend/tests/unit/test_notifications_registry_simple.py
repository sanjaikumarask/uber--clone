from apps.notifications.services.registry import EVENT_REGISTRY, default_builder

def test_event_registry_contents():
    assert "DRIVER_RIDE_OFFER" in EVENT_REGISTRY
    assert "ws" in EVENT_REGISTRY["RIDE_ASSIGNED"]["channels"]

def test_default_builder():
    data = {"key": "value"}
    assert default_builder(data) == data
