from unittest.mock import patch, MagicMock
from apps.rides.services.distance import get_planned_route, haversine_km

@patch("apps.rides.services.distance.settings")
@patch("apps.rides.services.distance.requests")
def test_fallback_on_api_failure(mock_req, mock_settings):
    # Setup API Key to force attempt
    mock_settings.GOOGLE_MAPS_API_KEY = "dummy_key"
    
    # Simulate API Failure
    mock_req.get.side_effect = Exception("Network Error")
    
    # Call with distinct coordinates
    # (0,0) to (1,0) is approx 111km
    res = get_planned_route((0,0), (1,0))
    
    # Verify Fallback was used (Haversine result)
    assert 110 < res["distance_km"] < 112
    # Check estimated duration (30km/h avg) -> ~222 min
    assert 200 < res["duration_min"] < 240

def test_same_coordinates():
    # Force Fallback mode (no API Key)
    with patch("apps.rides.services.distance.settings.GOOGLE_MAPS_API_KEY", None):
        res = get_planned_route((10.0, 10.0), (10.0, 10.0))
        assert res["distance_km"] == 0.0
        assert res["duration_min"] == 0.0

def test_extreme_coordinates():
    # North Pole to South Pole
    # Lat +90 to -90. Distance is half circumference (~20000km)
    dist = haversine_km(90, 0, -90, 0)
    assert 19900 < dist < 20100
    
    # Antimeridian crossing? Haversine handles this?
    # (0, 179) to (0, -179). Distance ~222km (2 degrees via 180)
    # Haversine uses shortest path (great circle)
    dist_cross = haversine_km(0, 179, 0, -179)
    assert 220 < dist_cross < 225
