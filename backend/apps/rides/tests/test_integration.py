import pytest
from rest_framework import status
from unittest.mock import patch, MagicMock
from apps.rides.models import Ride
from apps.drivers.models import Driver
from decimal import Decimal

@pytest.mark.django_db
class TestRideBookingIntegration:
    
    @pytest.fixture(autouse=True)
    def clear_cache(self):
        """Clear cache before each test to prevent idempotency key leakage"""
        from django.core.cache import cache
        cache.clear()
    
    @pytest.fixture
    def setup_driver(self, db, driver_user):
        """Create a verified, online driver for matching"""
        from apps.drivers.models import DriverStats
        driver = Driver.objects.get(user=driver_user)
        driver.is_verified = True
        driver.status = Driver.Status.ONLINE
        # Approximate location (Chennai Central)
        driver.last_lat = 13.0827
        driver.last_lng = 80.2707
        driver.save()
        
        # Ensure stats exist
        DriverStats.objects.get_or_create(driver=driver)
        return driver

    @patch('apps.rides.services.distance.requests.get')
    def test_successful_ride_booking_flow(self, mock_get, authenticated_rider_client, setup_driver):
        """
        Test the end-to-end flow:
        1. User requests ride
        2. Backend estimates fare (mocked Google Maps)
        3. Ride is created in SEARCHING status
        4. Matching engine runs and offers to nearby driver
        """
        # Mock Google Directions API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "OK",
            "routes": [{
                "overview_polyline": {"points": "mock_polyline"},
                "legs": [{
                    "distance": {"value": 5000}, # 5km
                    "duration": {"value": 600}  # 10 min
                }]
            }]
        }
        mock_get.return_value = mock_response

        # Mock Redis GEO search (internal service)
        # Instead of mocking redis directly, we rely on the DB fallback or mock the service
        with patch('apps.drivers.services.geo.get_nearby_driver_ids') as mock_geo:
            mock_geo.return_value = [setup_driver.id]
            
            payload = {
                "pickup_lat": 13.0827,
                "pickup_lng": 80.2707,
                "drop_lat": 13.0569,
                "drop_lng": 80.2425,
                "vehicle_type": "go"
            }
            
            # 1. API Call
            response = authenticated_rider_client.post("/api/rides/request/", payload)
            
            # 2. Assert Response
            assert response.status_code == status.HTTP_201_CREATED
            ride_id = response.data['id']
            
            # 3. Verify Database
            ride = Ride.objects.get(id=ride_id)
            assert ride.status in [Ride.Status.SEARCHING, Ride.Status.OFFERED]
            assert ride.planned_distance_km == 5.0
            
            # 4. Success check on matching (Matching happens on transaction commit)
            # In tests, we need to mock the locking service
            with patch('apps.drivers.services.geo.is_driver_locked', return_value=False), \
                 patch('apps.drivers.services.geo.lock_driver_for_offer', return_value=True):
                
                from apps.rides.services.matching import find_driver_and_offer_ride
                find_driver_and_offer_ride(ride.id)
                
                ride.refresh_from_db()
                assert ride.driver == setup_driver
                assert ride.status == Ride.Status.OFFERED

    def test_ride_booking_idempotency(self, authenticated_rider_client):
        """Test that duplicate requests with same idempotency key return cached response"""
        payload = {
            "pickup_lat": 13.0827,
            "pickup_lng": 80.2707,
            "drop_lat": 13.0569,
            "drop_lng": 80.2425,
        }
        headers = {'HTTP_X_IDEMPOTENCY_KEY': 'unique-key-123'}
        
        # First request
        resp1 = authenticated_rider_client.post("/api/rides/request/", payload, **headers)
        assert resp1.status_code == status.HTTP_201_CREATED
        
        # Second identical request
        resp2 = authenticated_rider_client.post("/api/rides/request/", payload, **headers)
        assert resp2.status_code == status.HTTP_201_CREATED
        
        data1 = resp1.data if hasattr(resp1, 'data') else resp1.json()
        data2 = resp2.data if hasattr(resp2, 'data') else resp2.json()
        assert data1['id'] == data2['id']
        
        # Verify only 1 ride exists in the DB for this scenario
        assert Ride.objects.count() == 1

    def test_prevent_active_ride_overlap(self, authenticated_rider_client, sample_ride):
        """User cannot book a ride if they already have one active"""
        payload = {
            "pickup_lat": 13.0827,
            "pickup_lng": 80.2707,
            "drop_lat": 13.0569,
            "drop_lng": 80.2425,
        }
        
        response = authenticated_rider_client.post("/api/rides/request/", payload)
        assert response.status_code == status.HTTP_409_CONFLICT
        assert "Active ride exists" in response.data['error']

    def test_invalid_location_coordinates(self, authenticated_rider_client):
        """Test failure when coordinates are out of range or missing"""
        payload = {
            "pickup_lat": "invalid",
            "pickup_lng": 80.2707,
        }
        response = authenticated_rider_client.post("/api/rides/request/", payload)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch('apps.rides.services.matching.find_driver_and_offer_ride')
    def test_no_driver_available_scenario(self, mock_matching, authenticated_rider_client):
        """Test system behavior when no drivers are found nearby"""
        with patch('apps.drivers.services.geo.get_nearby_driver_ids') as mock_geo:
            mock_geo.return_value = [] # No drivers
            
            payload = {
                "pickup_lat": 13.0827,
                "pickup_lng": 80.2707,
                "drop_lat": 13.0569,
                "drop_lng": 80.2425,
            }
            
            response = authenticated_rider_client.post("/api/rides/request/", payload)
            assert response.status_code == status.HTTP_201_CREATED
            
            # The ride is created but remains in SEARCHING
            ride = Ride.objects.get(id=response.data['id'])
            # Manually trigger matching
            with patch('apps.drivers.services.geo.is_driver_locked', return_value=False), \
                 patch('apps.drivers.services.geo.lock_driver_for_offer', return_value=True):
                from apps.rides.services.matching import find_driver_and_offer_ride
                find_driver_and_offer_ride(ride.id)
            
            ride.refresh_from_db()
            assert ride.status == Ride.Status.SEARCHING
            assert ride.driver is None
