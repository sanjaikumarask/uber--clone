"""
Unit Tests for Ride Models and Business Logic
"""
import pytest
from decimal import Decimal
from django.utils import timezone
from django.contrib.auth import get_user_model

from apps.rides.models import Ride
from apps.drivers.models import Driver
from apps.rides.services.otp import generate_and_attach_otp
from apps.rides import fare_config

User = get_user_model()


@pytest.mark.django_db
class TestRideModel:
    """Test Ride model"""

    def setup_method(self):
        self.rider = User.objects.create_user(
            username="rider",
            phone="9876543210",
            password="pass123",
            role="rider"
        )
        self.driver_user = User.objects.create_user(
            username="driver",
            phone="1234567890",
            password="pass123",
            role="driver"
        )
        self.driver = Driver.objects.get(user=self.driver_user)

    def test_create_ride(self):
        """Test creating a new ride"""
        ride = Ride.objects.create(
            rider=self.rider,
            pickup_lat=13.0827,
            pickup_lng=80.2707,
            # pickup_address="Chennai Central",
            drop_lat=13.0569,
            drop_lng=80.2425,
            # drop_address="Marina Beach",
            planned_distance_km=5.2,
            planned_duration_min=15,
            # estimated_fare=Decimal("120.00")
        )
        
        assert ride.id is not None
        assert ride.status == Ride.Status.SEARCHING
        assert ride.rider == self.rider
        assert ride.planned_distance_km == 5.2

    def test_ride_status_transitions(self):
        """Test ride status transitions"""
        ride = Ride.objects.create(
            rider=self.rider,
            pickup_lat=13.0827,
            pickup_lng=80.2707,
            drop_lat=13.0569,
            drop_lng=80.2425
        )
        
        # PENDING -> SEARCHING
        ride.status = Ride.Status.SEARCHING
        ride.save()
        assert ride.status == Ride.Status.SEARCHING
        
        # SEARCHING -> ASSIGNED
        ride.driver = self.driver
        ride.status = Ride.Status.ASSIGNED
        ride.save()
        assert ride.status == Ride.Status.ASSIGNED
        
        # ASSIGNED -> ARRIVED
        ride.status = Ride.Status.ARRIVED
        ride.arrived_at = timezone.now()
        ride.save()
        assert ride.status == Ride.Status.ARRIVED
        
        # ARRIVED -> ONGOING
        ride.status = Ride.Status.ONGOING
        ride.started_at = timezone.now()
        ride.save()
        assert ride.status == Ride.Status.ONGOING
        
        # ONGOING -> COMPLETED
        ride.status = Ride.Status.COMPLETED
        ride.completed_at = timezone.now()
        ride.final_fare = Decimal("150.00")
        ride.save()
        assert ride.status == Ride.Status.COMPLETED

    def test_ride_cancellation(self):
        """Test ride cancellation"""
        ride = Ride.objects.create(
            rider=self.rider,
            pickup_lat=13.0827,
            pickup_lng=80.2707,
            drop_lat=13.0569,
            drop_lng=80.2425,
            status=Ride.Status.SEARCHING
        )
        
        ride.status = Ride.Status.CANCELLED
        ride.cancelled_at = timezone.now()
        ride.cancelled_by = "rider"
        ride.save()
        
        assert ride.status == Ride.Status.CANCELLED
        assert ride.cancelled_by == "rider"


@pytest.mark.django_db
class TestOTPService:
    """Test OTP generation"""

    def setup_method(self):
        self.rider = User.objects.create_user(
            username="rider",
            phone="9876543210",
            password="pass123",
            role="rider"
        )
        self.ride = Ride.objects.create(
            rider=self.rider,
            pickup_lat=13.0827,
            pickup_lng=80.2707,
            drop_lat=13.0569,
            drop_lng=80.2425,
            status=Ride.Status.ARRIVED
        )

    def test_generate_otp(self):
        """Test OTP generation"""
        otp = generate_and_attach_otp(self.ride)
        
        assert otp is not None
        assert len(otp) == 4
        assert otp.isdigit()


@pytest.mark.django_db
class TestFareConfig:
    """Test fare configuration"""

    def test_fare_config_values(self):
        """Test fare configuration values are set"""
        assert fare_config.BASE_FARE > 0
        assert fare_config.PER_KM_RATE > 0
        assert fare_config.PER_MIN_RATE > 0
        assert fare_config.MINIMUM_FARE > 0
        assert fare_config.PLATFORM_COMMISSION_PERCENT > 0
