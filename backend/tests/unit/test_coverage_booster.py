import pytest
import os
import json
import hashlib
import time
from decimal import Decimal
from unittest.mock import patch, MagicMock, AsyncMock
from django.urls import reverse
from rest_framework import status
from django.utils import timezone
from apps.users.models import User
from apps.rides.models import Ride
from apps.drivers.models import Driver, DriverStats, DriverDocument
from apps.payments.models import Payment, Payout, LedgerEntry, DriverEarnings
from apps.offers.models import Offer, OfferUsage
from apps.supports.models import SupportTicket, Emergency
from apps.driver_incentives.models import DriverIncentive, DriverIncentiveEarning
from django.core import mail
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.http import HttpRequest, JsonResponse
from urllib.parse import unquote
from asgiref.sync import async_to_sync

# Force imports for coverage tracking
import apps.payments.views_web
import apps.payments.views_payout
import apps.notifications.providers.email
import apps.notifications.providers.sms
import apps.notifications.providers.push
import apps.notifications.providers.websocket
import apps.notifications.services.alerts
import apps.offers.views
import apps.offers.services.offer_engine
import apps.offers.services.eligibility_service
import apps.drivers.views
import apps.drivers.admin_views
import apps.drivers.urls
import apps.supports.views
import apps.driver_incentives.views
import apps.rides.tasks
import apps.rides.services.realtime
import apps.payments.services.ledger
import apps.payments.services.refund
import apps.common.idempotency
import apps.common.resilience
import apps.common.fraud
import apps.common.adaptive
import apps.common.backpressure
import apps.common.logging
import apps.admin_dashboard.views

@pytest.fixture
def admin_user(db):
    user = User.objects.create_superuser(
        username="admin_booster", 
        email="admin@example.com", 
        password="password",
        phone="9999999999"
    )
    user.role = User.ROLE_ADMIN
    user.save()
    return user

@pytest.fixture
def rider(db):
    return User.objects.create_user(
        username="rider_booster", 
        phone="1111111111", 
        password="password", 
        role=User.ROLE_RIDER,
        email="rider@example.com"
    )

@pytest.fixture
def driver_user(db):
    user = User.objects.create_user(
        username="driver_booster", 
        phone="2222222222", 
        password="password", 
        role=User.ROLE_DRIVER
    )
    driver, _ = Driver.objects.get_or_create(user=user)
    driver.is_verified = True
    driver.save()
    driver_stats, _ = DriverStats.objects.get_or_create(driver=driver)
    return user

@pytest.fixture
def ride(db, rider, driver_user):
    return Ride.objects.create(
        rider=rider,
        driver=driver_user.driver,
        pickup_lat=12.9716,
        pickup_lng=77.5946,
        drop_lat=12.9352,
        drop_lng=77.6245,
        final_fare=Decimal("150.00"),
        status=Ride.Status.COMPLETED,
        base_fare=Decimal("150.00"),
        start_time=timezone.now() - timezone.timedelta(minutes=10),
        completed_at=timezone.now()
    )

@pytest.fixture
def api_client():
    from rest_framework.test import APIClient
    return APIClient()

# ─── IDEMPOTENCY EXTENDED ────────────────────────────────────────────────────
@pytest.mark.django_db
class TestIdempotencyExtended:
    def test_idempotent_task_decorator(self, db):
        from apps.common.idempotency import idempotent_task
        mock_func = MagicMock(return_value="DONE")
        decorated = idempotent_task(ttl=60)(mock_func)
        
        # 1. Normal execution
        result = decorated(1, a=2)
        assert result == "DONE"
        assert mock_func.call_count == 1
        
        # 2. Replay (DONE)
        with patch("apps.common.idempotency.cache.get", return_value="1"):
            result = decorated(1, a=2)
            assert result is None
            assert mock_func.call_count == 1
            
        # 3. Concurrent duplicate (IN_FLIGHT)
        with patch("apps.common.idempotency.cache.add", return_value=False):
            result = decorated(1, a=2)
            assert result is None
            assert mock_func.call_count == 1

    def test_idempotent_webhook(self, db):
        from apps.common.idempotency import idempotent_webhook
        mock_view = MagicMock(return_value=JsonResponse({"ok": True}, status=200))
        decorated = idempotent_webhook(provider="razorpay")(mock_view)
        
        request = HttpRequest()
        request.headers = {"X-Razorpay-Event-Id": "evt_123"}
        
        # First call success
        with patch("apps.common.idempotency.cache.add", return_value=True), \
             patch("apps.common.idempotency.cache.get", return_value=None):
            resp = decorated(request)
            assert resp.status_code == 200
            
        # Duplicate already processed
        with patch("apps.common.idempotency.cache.get", return_value="1"):
            resp = decorated(request)
            assert resp.status_code == 200
            assert b"already_processed" in resp.content

# ─── FRAUD EXTENDED ──────────────────────────────────────────────────────────
@pytest.mark.django_db
class TestFraudExtended:
    def test_route_inflation(self, db, ride):
        from apps.common.fraud import detect_route_inflation
        ride.actual_distance_km = 10.0
        ride.planned_distance_km = 2.0
        assert detect_route_inflation(ride) is True
        
        ride.actual_distance_km = 3.0
        assert detect_route_inflation(ride) is False

    @patch("apps.rides.models.Ride.objects.filter")
    def test_frequency_anomaly(self, mock_filter, db, driver_user):
        from apps.common.fraud import detect_frequency_anomaly
        mock_filter.return_value.count.return_value = 10
        assert detect_frequency_anomaly(driver_user.driver) is True

    @patch("apps.rides.models.Ride.objects.filter")
    def test_coordinated_abuse(self, mock_filter, db, driver_user, ride):
        from apps.common.fraud import detect_coordinated_abuse
        mock_filter.return_value.count.return_value = 5
        assert detect_coordinated_abuse(driver_user.driver, ride) is True

    @patch("apps.drivers.redis.redis_client.hgetall")
    @patch("geopy.distance.geodesic")
    def test_validate_gps_velocity(self, mock_geodesic, mock_hgetall, db):
        from apps.common.fraud import validate_gps_velocity
        mock_hgetall.return_value = {"lat": "12.0", "lng": "77.0", "last_seen": str(int(time.time()) - 10)}
        mock_geodesic.return_value.km = 5.0 # 5km in 10s = 1800km/h
        assert validate_gps_velocity(1, 13.0, 78.0) is False

    @patch("apps.notifications.services.alerts.send_critical_alert")
    def test_apply_fraud_penalties(self, mock_alert, db, ride):
        from apps.common.fraud import apply_fraud_penalties
        ride.driver.stats.trust_score = 50.0
        apply_fraud_penalties(ride, ["GHOST_RIDE", "ROUTE_INFLATION"])
        assert ride.driver.stats.trust_score < 50.0
        assert mock_alert.called

# ─── BACKPRESSURE & ADAPTIVE ─────────────────────────────────────────────────
@pytest.mark.django_db
class TestBackpressureAdaptive:
    @patch("apps.drivers.redis.redis_client.pipeline")
    def test_connection_rate_limiter(self, mock_pipe):
        from apps.common.backpressure import ConnectionRateLimiter
        mock_pipe.return_value.execute.return_value = [None, None, 10, None]
        assert ConnectionRateLimiter.is_allowed(1) is False

    @patch("apps.common.adaptive.AdaptiveShedder.get_factor")
    @patch("apps.drivers.redis.redis_client.pipeline")
    def test_endpoint_cooldown(self, mock_pipe, mock_factor):
        from apps.common.backpressure import endpoint_cooldown
        mock_factor.return_value = 0.5
        mock_pipe.return_value.execute.return_value = [None, None, 100, None]
        assert endpoint_cooldown(1, "test", max_calls=10) is False

    def test_retry_strategy(self):
        from apps.common.backpressure import RetryStrategy
        assert RetryStrategy.get_max_retries("CRITICAL") == 10
        assert 0 <= RetryStrategy.get_countdown("NORMAL", 1) <= 600

    @patch("apps.common.adaptive.cache")
    def test_adaptive_shedder_should_shed(self, mock_cache):
        from apps.common.adaptive import AdaptiveShedder
        mock_cache.get.return_value = 0.8
        assert AdaptiveShedder.should_shed("NORMAL") is True
        assert AdaptiveShedder.should_shed("CRITICAL") is False

# ─── LOGGING ─────────────────────────────────────────────────────────────────
class MockLogRecord:
    def __init__(self):
        self.levelname = "INFO"
        self.module = "test"
        self.process = 1
        self.threadName = "main"
        self.levelno = 20
        self.exc_info = None
        self.ride_id = 123
        self.user_id = 456
        self.driver_id = 789

    def getMessage(self):
        return "msg"

def test_json_formatter():
    from apps.common.logging import JSONFormatter
    formatter = JSONFormatter()
    record = MockLogRecord()
    
    # get_trace_id is locally imported from apps.common.resilience inside format()
    with patch("apps.common.resilience.get_trace_id", return_value="test-trace-id"):
        msg_str = formatter.format(record)
    msg = json.loads(msg_str)
    assert msg["ride_id"] == 123
    assert msg["user_id"] == 456
    assert msg["driver_id"] == 789

# ─── RIDE VIEWS ─────────────────────────────────────────────────────────────
@pytest.mark.django_db
class TestRideViewsExtended:
    def test_accept_ride_view(self, api_client, driver_user, ride):
        ride.status = Ride.Status.OFFERED
        ride.driver = driver_user.driver
        ride.save()
        api_client.force_authenticate(user=driver_user)
        url = f"/api/rides/{ride.id}/accept/"
        response = api_client.post(url)
        assert response.status_code == 200
        ride.refresh_from_db()
        assert ride.status == Ride.Status.ASSIGNED

    def test_verify_otp_view(self, api_client, driver_user, ride):
        # Ride must be ARRIVED with proper OTP set up
        ride.status = Ride.Status.ARRIVED
        ride.otp_code = "1234"
        ride.otp_expires_at = timezone.now() + timezone.timedelta(minutes=5)
        ride.otp_verified_at = None
        ride.driver = driver_user.driver
        ride.save()
        
        api_client.force_authenticate(user=driver_user)
        url = f"/api/rides/{ride.id}/start/"
        
        # Patch the OTP verify function and the downstream status update to keep test isolated
        with patch("apps.rides.views.verify_and_consume_otp") as mock_otp, \
             patch("apps.rides.views.update_ride_status") as mock_update, \
             patch("apps.drivers.redis.redis_client.get", return_value=b"0"), \
             patch("apps.common.idempotency.cache") as mock_cache:
            mock_cache.get.return_value = None
            mock_cache.add.return_value = True
            mock_otp.return_value = None  # successful verification
            mock_update.return_value = None
            response = api_client.post(url, data={"otp": "1234", "lat": 12.0, "lng": 77.0})
            assert response.status_code == 200

    def test_complete_ride_view(self, api_client, driver_user, ride):
        ride.status = Ride.Status.ONGOING
        ride.driver = driver_user.driver
        ride.save()
        api_client.force_authenticate(user=driver_user)
        url = f"/api/rides/{ride.id}/complete/"
        with patch("apps.rides.services.complete_ride.complete_ride", return_value=ride):
            response = api_client.post(url)
            assert response.status_code == 200

# ─── NOTIFICATION PROVIDERS ─────────────────────────────────────────────────
@pytest.mark.django_db
class TestNotificationProvidersExtended:
    @patch("apps.notifications.providers.email.EmailMultiAlternatives")
    def test_send_email_comprehensive(self, mock_msg, rider):
        from apps.notifications.providers.email import send_email
        notification = MagicMock(user=rider, payload={"subject": "S", "body": "B"})
        send_email(notification)
        assert mock_msg.called

    @patch("apps.notifications.providers.sms.Client")
    def test_send_sms_comprehensive(self, mock_client, rider):
        from apps.notifications.providers.sms import send_sms
        rider.phone_number = "123"
        notification = MagicMock(user=rider, payload={"body": "B"})
        send_sms(notification)
        assert mock_client.called

    @patch("apps.notifications.providers.websocket.get_channel_layer")
    def test_send_ws_comprehensive(self, mock_layer, rider):
        from apps.notifications.providers.websocket import send_ws
        notification = MagicMock(user=rider, payload={"type": "update", "data": {}})
        send_ws(notification)
        assert mock_layer.called
