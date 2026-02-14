from apps.tracking.geo import haversine_m, snap_to_route, is_deviated, accumulate_distance

class TestGeoUtils:
    def test_haversine_distance(self):
        # Known distance: Bangalore (12.9716, 77.5946) to Mysore (12.2958, 76.6394) ~ 127km = 127000m
        dist = haversine_m(12.9716, 77.5946, 12.2958, 76.6394)
        # Assert within range
        assert 125000 < dist < 139000

    def test_snap_to_route_logic(self):
        # Using small offsets
        # Route points
        p1 = (12.9716, 77.5946)
        p2 = (12.9800, 77.6000) # Further away
        route = [p1, p2]
        
        # Point strictly closer to p1
        # 0.0001 deg is roughly 11 meters
        test_lat = 12.9717 
        test_lng = 77.5947
        
        closest, dist_m = snap_to_route(test_lat, test_lng, route)
        
        assert closest == p1
        assert dist_m < 200 # Should be very close

    def test_is_deviated(self):
        assert is_deviated(60) is True
        assert is_deviated(49) is False

    def test_accumulate_distance(self):
        p1 = (12.9716, 77.5946)
        p2 = (12.9726, 77.5956) # Roughly 150m away
        
        dist_km = accumulate_distance(p1, p2)
        assert 0.1 < dist_km < 0.2
