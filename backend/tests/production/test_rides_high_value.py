import pytest
import uuid
import time
from decimal import Decimal
from unittest.mock import patch, MagicMock
from django.utils import timezone
from django.db import transaction
from rest_framework import status

from apps.rides.models import Ride
from apps.drivers.models import Driver
from apps.users.models import User
from apps.rides.tasks import driver_accept_timeout, auto_resolve_stuck_rides

@pytest.mark.django_db(transaction=True)
class TestRidesHighValue:
    """
    Principal Engineer's Ride Lifecycle Resilience Suite.
    Focuses on stale states, concurrent timers, and fraud prevention.
    """

    def setup_method(self):
        self.rider = User.objects.create_user(username=f"rider_{uuid.uuid4().hex[:4]}", role="rider")
        self.driver_user = User.objects.create_user(username=f"driver_{uuid.uuid4().hex[:4]}", role="driver")
        self.driver = self.driver_user.driver
        self.driver.status = Driver.Status.ONLINE
        self.driver.save()
        
    # --- 1. Concurrency & Racing Timers ---

    def test_accept_ride_vs_timeout_timer_race(self):
        """
        WHY: Prevents 'Double State Mutation'. If a driver clicks 'Accept' at the 
        exact millisecond the Celery timeout task runs, one MUST fail cleanly.
        """
        ride = Ride.objects.create(
            rider=self.rider, driver=self.driver, status=Ride.Status.OFFERED,
            pickup_lat=12.9716, pickup_lng=77.5946, drop_lat=12.9716, drop_lng=77.6000
        )
        
        # 1. Start Celery task (simulated execution)
        # 2. Concurrently call AcceptRideView.post
        from rest_framework.test import APIRequestFactory, force_authenticate
        from apps.rides.views import AcceptRideView
        
        factory = APIRequestFactory()
        request = factory.post(f"/api/v1/rides/{ride.id}/accept/")
        force_authenticate(request, user=self.driver_user)
        view = AcceptRideView.as_view()

        # Simulate race: select_for_update() in task wins the lock
        with transaction.atomic():
            # Task locks the ride
            locked_ride = Ride.objects.select_for_update().get(id=ride.id)
            
            # The view should hang/timeout or fail on status check once lock is released
            # Since we are in the same process/thread here, we'll simulate the status change
            driver_accept_timeout(ride.id, self.driver.id)
            
            # Now the view tries to execute (after the task released the lock)
            response = view(request, ride_id=ride.id)
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "SEARCHING" in response.data["error"]

    # --- 2. Fraud & Security Enforcements ---

    @patch("apps.drivers.redis.redis_client.get")
    @patch("apps.drivers.redis.redis_client.incr")
    def test_otp_brute_force_flags_fraud(self, mock_incr, mock_get):
        """
        WHY: Security Enforcement. If a driver tries to guess the OTP 5 times, 
        the ride is locked and flagged for review to prevent ride hijacking.
        """
        ride = Ride.objects.create(
            rider=self.rider, driver=self.driver, status=Ride.Status.ARRIVED,
            otp_code="1234", pickup_lat=0, pickup_lng=0, drop_lat=0, drop_lng=0
        )
        
        # Mock 5 failed attempts reached
        mock_get.return_value = b"5"
        
        from rest_framework.test import APIRequestFactory, force_authenticate
        from apps.rides.views import VerifyOtpView
        
        factory = APIRequestFactory()
        request = factory.post(f"/api/v1/rides/{ride.id}/verify-otp/", {"otp": "0000"}, format="json")
        force_authenticate(request, user=self.driver_user)
        view = VerifyOtpView.as_view()
        
        response = view(request, ride_id=ride.id)
        
        assert response.status_code == 429
        ride.refresh_from_db()
        assert ride.is_fraud_flagged is True

    # --- 3. Stale State Maintenance ---

    def test_auto_resolve_maintenance_skips_recent_activity(self):
        """
        WHY: Data Integrity. The system-level cleanup task must not cancel a 
        ride that just started, even if it was SEARCHING for 15 minutes prior.
        """
        # Create a ride that was SEARCHING for 20 mins, but just got ASSIGNED 1 min ago
        now = timezone.now()
        ride = Ride.objects.create(
            rider=self.rider, status=Ride.Status.ASSIGNED,
            pickup_lat=0, pickup_lng=0, drop_lat=0, drop_lng=0
        )
        # Manually force created_at and updated_at to stale states (bypass auto_now)
        Ride.objects.filter(id=ride.id).update(
            created_at=now - timezone.timedelta(minutes=20),
            updated_at=now - timezone.timedelta(minutes=1)
        )
        ride.refresh_from_db()
        
        auto_resolve_stuck_rides()
        
        ride.refresh_from_db()
        assert ride.status == Ride.Status.ASSIGNED  # Must NOT be cancelled

    # --- 4. API Resilience: Idempotency Collision ---

    def test_create_ride_idempotency_key_collision(self):
        """
        WHY: Prevents Double Booking. If an unstable network causes the client
        to send the same 'X-Idempotency-Key' twice in 100ms, only one ride
        should be created.
        """
        from rest_framework.test import APIClient
        from rest_framework_simplejwt.tokens import AccessToken

        client = APIClient()
        token = AccessToken.for_user(self.rider)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        idem_key = f"collision_{uuid.uuid4().hex}"

        # First call — seed the IN_FLIGHT marker
        with patch("apps.common.idempotency.cache.add", return_value=False), \
             patch("apps.common.idempotency.cache.get", return_value="IN_FLIGHT"):
            response = client.post(
                "/api/rides/request/",
                {"pickup_lat": 12.9716, "pickup_lng": 77.5946,
                 "drop_lat": 12.9716, "drop_lng": 77.6000},
                format="json",
                HTTP_X_IDEMPOTENCY_KEY=idem_key,
            )

        # Middleware returns 409 when cache.add returns False (key in-flight)
        assert response.status_code == 409
        assert "already in progress" in response.content.decode().lower()
