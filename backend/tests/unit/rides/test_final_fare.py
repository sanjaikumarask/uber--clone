import pytest
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from unittest.mock import MagicMock, patch
from apps.rides.services.final_fare import calculate_final_fare, get_fare_breakdown
from apps.rides.models import Ride

@pytest.mark.django_db
class TestFinalFareCalculator:

    @patch("apps.rides.services.final_fare.get_surge", return_value=1.0)
    @patch("apps.rides.fare_models.FareConfig.get_for")
    def test_calculate_final_fare_basic(self, mock_config, mock_surge):
        config = MagicMock()
        config.base_fare = Decimal("50.00")
        config.base_distance_km = Decimal("2.0")
        config.per_km_rate = Decimal("12.00")
        config.waiting_free_minutes = 5
        config.waiting_per_minute = Decimal("2.00")
        config.minimum_fare = Decimal("60.00")
        config.surge_multiplier = Decimal("1.00")
        mock_config.return_value = config
        
        ride = MagicMock(spec=Ride)
        ride.vehicle_type = "go"
        ride.actual_distance_km = 5.0 # 3.0km extra
        ride.waiting_seconds = 600 # 10 mins -> 5 mins billable
        ride.discount_amount = Decimal("10.00")
        ride.base_fare = Decimal("100.00") # Original quote
        ride.planned_distance_km = 4.0
        ride.pickup_lat = 12.97
        ride.pickup_lng = 77.59
        
        # Calculation:
        # Distance: 3.0 * 12 = 36
        # Waiting: 5 * 2 = 10
        # Subtotal: (50 + 36 + 10) * 1.0 = 96
        # Final: 96 - 10 = 86
        
        fare = calculate_final_fare(ride)
        assert fare == Decimal("86.00")

    @patch("apps.rides.services.final_fare.get_surge", return_value=2.0)
    @patch("apps.rides.fare_models.FareConfig.get_for")
    def test_calculate_final_fare_with_surge(self, mock_config, mock_surge):
        config = MagicMock()
        config.base_fare = Decimal("50.00")
        config.base_distance_km = Decimal("2.0")
        config.per_km_rate = Decimal("10.00")
        config.waiting_free_minutes = 2
        config.waiting_per_minute = Decimal("2.00")
        config.minimum_fare = Decimal("50.00")
        mock_config.return_value = config
        
        ride = MagicMock(spec=Ride)
        ride.actual_distance_km = 2.0 # 0 extra
        ride.waiting_seconds = 0
        ride.discount_amount = Decimal("0.00")
        ride.base_fare = Decimal("300.00") # Very high quote to avoid cap
        ride.planned_distance_km = 2.0
        
        # Calculation:
        # Distance: 0
        # Waiting: 0
        # Subtotal: (50 + 0 + 0) * 2.0 = 100
        # Final: 100
        
        fare = calculate_final_fare(ride)
        assert fare == Decimal("100.00")

    @patch("apps.rides.services.final_fare.get_surge", return_value=1.0)
    @patch("apps.rides.fare_models.FareConfig.get_for")
    def test_calculate_final_fare_shock_cap(self, mock_config, mock_surge):
        config = MagicMock()
        config.base_fare = Decimal("50.00")
        config.per_km_rate = Decimal("100.00") # Extreme rate
        config.base_distance_km = Decimal("0.0")
        config.waiting_free_minutes = 0
        config.waiting_per_minute = Decimal("0.0")
        config.minimum_fare = Decimal("30.0")
        mock_config.return_value = config
        
        ride = MagicMock(spec=Ride)
        ride.actual_distance_km = 10.0
        ride.waiting_seconds = 0
        ride.discount_amount = Decimal("0.00")
        ride.base_fare = Decimal("100.00") # Original quote
        ride.planned_distance_km = 10.0
        
        # Calculation:
        # Subtotal: (50 + 1000) = 1050
        # Cap: 1.5 * 100 = 150
        
        fare = calculate_final_fare(ride)
        assert fare == Decimal("150.00")

    @patch("apps.rides.services.final_fare.get_surge", return_value=1.0)
    @patch("apps.rides.fare_models.FareConfig.get_for")
    def test_get_fare_breakdown(self, mock_config, mock_surge):
        config = MagicMock()
        config.base_fare = Decimal("40.00")
        config.base_distance_km = Decimal("0.0")
        config.per_km_rate = Decimal("10.00")
        config.minimum_fare = Decimal("30.00")
        config.waiting_free_minutes = 0
        config.waiting_per_minute = Decimal("1.00")
        mock_config.return_value = config
        
        ride = MagicMock(spec=Ride)
        ride.vehicle_type = "go"
        ride.actual_distance_km = 5.0
        ride.waiting_seconds = 60
        ride.discount_amount = Decimal("5.00")
        ride.tip_amount = Decimal("20.00")
        
        breakdown = get_fare_breakdown(ride)
        assert breakdown["total_with_tip"] == "106.00" # (40 + 50 + 1) - 5 + 20 = 106
        assert breakdown["actual_distance_km"] == 5.0
        assert breakdown["waiting_charge"] == "1.00"
