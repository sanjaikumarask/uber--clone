from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from django.test import TestCase

from apps.users.models import User
from apps.drivers.models import Driver
from apps.rides.models import Ride
from apps.rides.fare_models import FareConfig
from apps.rides.services.lifecycle import update_ride_status
from apps.rides.services.waiting_detector import _cache_key
from apps.rides.services.complete_ride import complete_ride
from django.core.cache import cache


class EndToEndFareTests(TestCase):
    def setUp(self):
        # 1. Provide an identical environment to the user's manual FareConfig
        self.config = FareConfig.objects.create(
            vehicle_type="go",
            base_fare=Decimal("50.00"),            # 50 rs minimum charge
            base_distance_km=Decimal("2.00"),      # For the first 2km
            per_km_rate=Decimal("20.00"),          # 20 rs/km afterwards
            waiting_free_minutes=2,                # Zero charge up to 2m
            waiting_per_minute=Decimal("5.00"),    # 5 rs/minute waiting
            minimum_fare=Decimal("50.00"),         # Do not enforce a 60rs floor
            surge_multiplier=Decimal("1.00"),      # No surge
            platform_commission_pct=Decimal("20.00")
        )

        # 2. Setup Driver & Rider Mock Data
        self.rider_user = User.objects.create_user(
            username="rider123", phone="+10000000000", role="RIDER"
        )
        self.driver_user = User.objects.create_user(
            username="driver456", phone="+10000000001", role="DRIVER"
        )
        self.driver = Driver.objects.create(
            user=self.driver_user, status="ONLINE", is_verified=True
        )

    def test_ideal_ride_no_waiting(self):
        """
        Scenario 1: Driver arrives, picks up immediately (0 wait time). 
        Rider takes a flawless 2.0km ride (no extra distance fee).
        Expectation: Ride costs exactly flat base_fare of ₹50.00.
        """
        ride = Ride.objects.create(
            rider=self.rider_user,
            driver=self.driver,
            vehicle_type="go",
            status=Ride.Status.ASSIGNED,
            pickup_lat="12.9716", pickup_lng="77.5946",
            drop_lat="12.9352", drop_lng="77.6245",
            planned_distance_km=Decimal("2.0"),
            base_fare=Decimal("50.00")
        )

        # Driver arrives, zero wait
        update_ride_status(ride, Ride.Status.ARRIVED)
        ride.arrived_at = timezone.now()
        ride.save()

        # Simulated "no wait" in redis
        cache.set(_cache_key(ride.id), {"accumulated_secs": 0, "is_waiting": False}, 60)

        # Trip starts and ends exactly at 2.0km
        update_ride_status(ride, Ride.Status.ONGOING)
        ride.otp_verified_at = timezone.now()
        ride.actual_distance_km = Decimal("2.0")
        ride.save()

        completed_ride = complete_ride(ride_id=ride.id)
        
        self.assertEqual(completed_ride.final_fare, Decimal("50.00"))
        self.assertEqual(completed_ride.fare_breakdown["distance_charge"], "0.00")
        self.assertEqual(completed_ride.fare_breakdown["waiting_charge"], "0.00")


    def test_heavy_traffic_waiting_charge(self):
        """
        Scenario 2: Driver arrived. Stood outside for 8 minutes (6 billable mintues).
        Drove long 6.5km route (4.5 billable km).
        Expectation: Base (50) + Distance (4.5*20 = 90) + Wait (6*5 = 30) = ₹170.00
        """
        ride = Ride.objects.create(
            rider=self.rider_user,
            driver=self.driver,
            vehicle_type="go",
            status=Ride.Status.ASSIGNED,
            pickup_lat="12.9716", pickup_lng="77.5946",
            drop_lat="12.9352", drop_lng="77.6245"
        )

        update_ride_status(ride, Ride.Status.ARRIVED)
        ride.arrived_at = timezone.now() - timedelta(minutes=8)
        ride.save()

        # Inject 8 minutes waiting into Redis (480 seconds)
        cache.set(_cache_key(ride.id), {"accumulated_secs": 480, "is_waiting": False}, 60)

        update_ride_status(ride, Ride.Status.ONGOING)
        ride.otp_verified_at = timezone.now()
        ride.actual_distance_km = Decimal("6.5") # (6.5km total - 2km base) = 4.5km billable
        ride.save()

        completed_ride = complete_ride(ride_id=ride.id)

        # Asserts
        self.assertEqual(completed_ride.final_fare, Decimal("170.00"))
        
        # Verify the fine-grained receipt breakdown math
        self.assertEqual(completed_ride.fare_breakdown["base_fare"], "50.00")
        self.assertEqual(completed_ride.fare_breakdown["distance_charge"], "90.00") # 4.5km * 20
        self.assertEqual(completed_ride.fare_breakdown["waiting_charge"], "30.00")  # (8m-2m free) * 5


    def test_minimum_fare_enforcement(self):
        """
        Scenario 3: A driver only drives 0.5km in a neighborhood with a high Minimum Fare requirement 
        (Floor set to ₹65.00 manually by Admin).
        Expectation: Math says 50 base + 0 distance + 0 waiting = 50. But enforced floor jumps it to ₹65.
        """
        # Override config specifically for this test
        self.config.minimum_fare = Decimal("65.00")
        self.config.save()

        ride = Ride.objects.create(
            rider=self.rider_user,
            driver=self.driver,
            vehicle_type="go",
            status=Ride.Status.ARRIVED,         # skipping assigned
            pickup_lat="12.0", pickup_lng="77.0",
            drop_lat="12.1", drop_lng="77.1",
        )
        
        # 0 wait
        cache.set(_cache_key(ride.id), {"accumulated_secs": 0, "is_waiting": False}, 60)
        
        update_ride_status(ride, Ride.Status.ONGOING)
        ride.actual_distance_km = Decimal("0.5")  # Less than base
        ride.save()

        completed_ride = complete_ride(ride_id=ride.id)

        # Normally 50... but minimum_fare floor applies!
        self.assertEqual(completed_ride.final_fare, Decimal("65.00"))
