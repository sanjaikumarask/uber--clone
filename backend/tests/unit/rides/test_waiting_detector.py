from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.rides.services.waiting_detector import (
    compute_speed_kmh,
    process_location_update,
    get_total_waiting_seconds,
)


@pytest.fixture(autouse=True)
def mock_cache():
    with patch("apps.rides.services.waiting_detector.cache") as mock:
        store = {}

        def get(key):
            return store.get(key)

        def set_val(key, val, ttl=None):
            store[key] = val

        def delete(key):
            store.pop(key, None)

        mock.get.side_effect = get
        mock.set.side_effect = set_val
        mock.delete.side_effect = delete
        yield mock


def test_compute_speed_kmh():
    # 1km in 60s should be 60km/h
    speed = compute_speed_kmh(0.0, 0.0, 0.0, 0.008993, 60)  # ~1km approx
    assert 59.0 < speed < 61.0
    assert compute_speed_kmh(0, 0, 0, 0, 0) == 0.0


def test_waiting_detection_debounce():
    ride_id = 123
    now = timezone.now()

    # Step 1: Slow ping 1 (No waiting yet, start debounce)
    res = process_location_update(ride_id, 0, 0, 0, 0.0001, 30)
    assert res["is_waiting"] is False
    assert res["event"] == "none"

    # Step 2: Slow ping 2 (After 61 seconds total slow time)
    with patch("django.utils.timezone.now", return_value=now + timedelta(seconds=61)):
        res = process_location_update(ride_id, 0, 0, 0, 0.0001, 31)
        assert res["is_waiting"] is True
        assert res["event"] == "waiting_started"


def test_waiting_ends_when_moving():
    ride_id = 123
    now = timezone.now()

    # Setup: Already waiting
    # We'll just manually set the state to simulate being in waiting state
    with patch("apps.rides.services.waiting_detector._get_state") as mock_get:
        mock_get.return_value = {
            "is_waiting": True,
            "waiting_since": (now - timedelta(seconds=120)).isoformat(),
            "accumulated_secs": 0,
            "low_speed_since": (now - timedelta(seconds=120)).isoformat(),
        }

        # Moving fast (100km/h)
        res = process_location_update(ride_id, 0, 0, 0.1, 0.1, 10)
        assert res["is_waiting"] is False
        assert res["event"] == "waiting_ended"
        assert res["accumulated_secs"] >= 120


def test_get_total_waiting_seconds():
    ride_id = 456
    now = timezone.now()

    with patch("apps.rides.services.waiting_detector._get_state") as mock_get:
        # Case 1: Not waiting, but has accumulated some
        mock_get.return_value = {
            "is_waiting": False,
            "waiting_since": None,
            "accumulated_secs": 300,
            "low_speed_since": None,
        }
        assert get_total_waiting_seconds(ride_id) == 300

        # Case 2: Currently waiting
        mock_get.return_value = {
            "is_waiting": True,
            "waiting_since": (now - timedelta(seconds=60)).isoformat(),
            "accumulated_secs": 100,
            "low_speed_since": (now - timedelta(seconds=120)).isoformat(),
        }
        assert get_total_waiting_seconds(ride_id) >= 160
