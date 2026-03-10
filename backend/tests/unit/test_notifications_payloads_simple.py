from apps.notifications.services.payloads import (
    ride_assigned_payload, 
    ride_started_payload, 
    ride_completed_payload
)

def test_payload_builders():
    data = {"driver_name": "Bob", "ride_id": 123, "vehicle": "Swift", "fare": 100}
    
    p1 = ride_assigned_payload(data)
    assert p1["ride_id"] == 123
    assert "Bob" in p1["body"]
    
    p2 = ride_started_payload(data)
    assert p2["title"] == "Ride Started"
    
    p3 = ride_completed_payload(data)
    assert p3["fare"] == 100
