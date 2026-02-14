"""
Pytest configuration and fixtures
"""
import pytest
from django.conf import settings
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    """Fixture for API client"""
    return APIClient()


@pytest.fixture
def rider_user(db):
    """Fixture for creating a rider user"""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    return User.objects.create_user(
        username="test_rider",
        phone="9876543210",
        password="testpass123",
        role="rider",
        first_name="Test",
        last_name="Rider"
    )


@pytest.fixture
def driver_user(db):
    """Fixture for creating a driver user"""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    return User.objects.create_user(
        username="test_driver",
        phone="1234567890",
        password="testpass123",
        role="driver",
        first_name="Test",
        last_name="Driver"
    )


@pytest.fixture
def admin_user(db):
    """Fixture for creating an admin user"""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    return User.objects.create_superuser(
        username="admin",
        phone="0000000000",
        password="admin123",
        role="admin"
    )


@pytest.fixture
def authenticated_rider_client(api_client, rider_user):
    """Fixture for authenticated rider client"""
    api_client.force_authenticate(user=rider_user)
    return api_client


@pytest.fixture
def authenticated_driver_client(api_client, driver_user):
    """Fixture for authenticated driver client"""
    api_client.force_authenticate(user=driver_user)
    return api_client


@pytest.fixture
def sample_ride(db, rider_user):
    """Fixture for creating a sample ride"""
    from apps.rides.models import Ride
    from decimal import Decimal
    
    return Ride.objects.create(
        rider=rider_user,
        pickup_lat=13.0827,
        pickup_lng=80.2707,
        pickup_address="Chennai Central",
        dropoff_lat=13.0569,
        dropoff_lng=80.2425,
        dropoff_address="Marina Beach",
        distance=5.2,
        duration=15,
        estimated_fare=Decimal("120.00")
    )


@pytest.fixture
def assigned_ride(db, rider_user, driver_user):
    """Fixture for creating a ride assigned to a driver"""
    from apps.rides.models import Ride
    from apps.drivers.models import Driver
    from decimal import Decimal
    
    driver = Driver.objects.get(user=driver_user)
    
    return Ride.objects.create(
        rider=rider_user,
        driver=driver,
        pickup_lat=13.0827,
        pickup_lng=80.2707,
        dropoff_lat=13.0569,
        dropoff_lng=80.2425,
        distance=5.2,
        estimated_fare=Decimal("120.00"),
        status=Ride.Status.ASSIGNED
    )


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """Automatically enable database access for all tests"""
    pass


@pytest.fixture
def mock_google_maps():
    """Fixture for mocking Google Maps API"""
    from unittest.mock import patch
    
    with patch('apps.rides.services.google_maps.get_planned_route') as mock:
        mock.return_value = {
            "polyline": "mock_polyline_data",
            "distance_km": 5.2,
            "duration_min": 15
        }
        yield mock


@pytest.fixture
def mock_payment_gateway():
    """Fixture for mocking payment gateway"""
    from unittest.mock import patch
    
    with patch('apps.payments.services.process_payment') as mock:
        mock.return_value = {
            "success": True,
            "transaction_id": "mock_txn_123",
            "amount": "120.00"
        }
        yield mock
