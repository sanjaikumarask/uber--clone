from unittest.mock import MagicMock
from apps.notifications.services.payloads import ride_assigned_payload, ride_completed_payload
from apps.notifications.services.retry import should_retry, get_retry_delay

def test_payload_ride_assigned():
    data = {
        "driver_name": "Dave",
        "ride_id": 123,
        "vehicle": "Tesla"
    }
    res = ride_assigned_payload(data)
    assert res["title"] == "Driver Assigned"
    assert "Dave" in res["body"]
    assert res["vehicle"] == "Tesla"

def test_retry_logic():
    mock_notif = MagicMock()
    
    # Attempt 0: Should retry, 10s delay
    mock_notif.retry_count = 0
    assert should_retry(mock_notif) is True
    assert get_retry_delay(mock_notif) == 10.0 # 10 * 2^0
    
    # Attempt 4: Should retry, 160s delay
    mock_notif.retry_count = 4
    assert should_retry(mock_notif) is True
    assert get_retry_delay(mock_notif) == 160.0 # 10 * 16
    
    # Attempt 5: Shouldn't retry
    mock_notif.retry_count = 5
    assert should_retry(mock_notif) is False
