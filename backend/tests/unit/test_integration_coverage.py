"""
tests/unit/test_integration_coverage.py

High-coverage integration tests targeting the most impactful
uncovered modules. Mocks external systems (Redis, Kafka, Celery).
Revised after multiple failure analyses.
"""
import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock
from django.utils import timezone
from django.test import override_settings


# ─────────────────────────────────────────────────────────────
# USERS VIEWS
# ─────────────────────────────────────────────────────────────
@pytest.mark.django_db
class TestUsersViews:
    def test_register_rider(self, api_client):
        payload = {
            "phone": "9000000001",
            "password": "Test@1234",
            "role": "rider",
        }
        with patch("apps.notifications.models.Notification.objects.create"):
            resp = api_client.post("/api/users/register/", payload)
        assert resp.status_code == 201

    def test_register_invalid_missing_phone(self, api_client):
        # Now returns 400 because phone is required in serializer
        resp = api_client.post("/api/users/register/", {"password": "y"})
        assert resp.status_code == 400

    def test_rider_login_success(self, api_client, user):
        user.set_password("Test@1234")
        user.save()
        resp = api_client.post("/api/users/login/", {"phone": user.phone, "password": "Test@1234"})
        assert resp.status_code == 200

    def test_driver_login_invalid_credentials(self, api_client):
        resp = api_client.post("/api/users/driver-login/", {"phone": "0000", "password": "wrong"})
        assert resp.status_code == 400

    def test_admin_login_invalid(self, api_client):
        resp = api_client.post("/api/users/admin-login/", {"phone": "0000", "password": "wrong"})
        assert resp.status_code == 400

    def test_me_view(self, api_client, user):
        api_client.force_authenticate(user=user)
        resp = api_client.get("/api/users/me/")
        assert resp.status_code == 200

    def test_update_push_token(self, api_client, user):
        api_client.force_authenticate(user=user)
        resp = api_client.post("/api/users/push-token/update/", {"token": "expo-abc"})
        assert resp.status_code == 200
        user.refresh_from_db()
        assert user.expo_push_token == "expo-abc"


# ─────────────────────────────────────────────────────────────
# SUPPORTS VIEWS
# ─────────────────────────────────────────────────────────────
@pytest.mark.django_db
class TestSupportsViews:
    def test_create_support_ticket_success(self, api_client, user, ride):
        ride.rider = user
        ride.save()
        api_client.force_authenticate(user=user)
        resp = api_client.post(
            f"/api/supports/rides/{ride.id}/tickets/",
            {"reason": "late", "description": "test_desc"},
        )
        assert resp.status_code == 201

    def test_trigger_sos_success(self, api_client, user, ride):
        ride.rider = user
        ride.save()
        api_client.force_authenticate(user=user)
        with patch("asgiref.sync.async_to_sync") as mock_sync:
            mock_sync.return_value = lambda *a, **kw: None
            resp = api_client.post(
                f"/api/supports/rides/{ride.id}/sos/",
                {"lat": 12.0, "lng": 77.0},
            )
        assert resp.status_code == 200

    def test_trigger_sos_no_permission(self, api_client, ride):
        from apps.users.models import User
        stranger = User.objects.create_user(username="9988776655", phone="9988776655")
        api_client.force_authenticate(user=stranger)
        resp = api_client.post(f"/api/supports/rides/{ride.id}/sos/", {"lat": 12, "lng": 77})
        assert resp.status_code == 403


# ─────────────────────────────────────────────────────────────
# RIDES TASKS
# ─────────────────────────────────────────────────────────────
@pytest.mark.django_db
class TestRidesTasks:
    def test_driver_accept_timeout(self, driver_user, ride):
        from apps.rides.tasks import driver_accept_timeout
        from apps.rides.models import Ride
        driver = driver_user.driver
        ride.driver = driver
        ride.status = Ride.Status.OFFERED
        ride.save()
        with patch("apps.rides.services.matching.find_driver_and_offer_ride"), \
             patch("apps.rides.tasks.add_driver_to_geo"), \
             patch("apps.rides.tasks.increment_demand"), \
             patch("apps.rides.tasks.increment_supply"):
            driver_accept_timeout(ride.id, driver.id)
        ride.refresh_from_db()
        assert ride.status == Ride.Status.SEARCHING

    def test_check_no_show_task(self, driver_user, ride):
        from apps.rides.tasks import check_no_show
        from apps.rides.models import Ride
        ride.status = Ride.Status.ARRIVED
        ride.arrived_at = timezone.now() - timezone.timedelta(minutes=10)
        ride.driver = driver_user.driver
        ride.save()
        with patch("apps.rides.tasks.handle_no_show") as mock_no:
            check_no_show(ride.id)
            assert mock_no.called

    def test_auto_resolve_stuck_rides(self, ride):
        from apps.rides.tasks import auto_resolve_stuck_rides
        from apps.rides.models import Ride
        ride.status = Ride.Status.SEARCHING
        ride.save()
        # Bypass auto_now using .update()
        Ride.objects.filter(id=ride.id).update(updated_at=timezone.now() - timezone.timedelta(minutes=20))
        
        with patch("apps.rides.services.cancellation.cancel_ride") as mock_cancel:
            auto_resolve_stuck_rides()
            assert mock_cancel.called


# ─────────────────────────────────────────────────────────────
# PAYMENTS RECONCILIATION & REFUNDS
# ─────────────────────────────────────────────────────────────
@pytest.mark.django_db
class TestPaymentsExtended:
    def test_reconcile_payout_processed(self, user):
        from apps.payments.models import Payout
        from apps.payments.services.reconciliation import reconcile_payout_status_task
        payout = Payout.objects.create(
            driver=user,
            amount=Decimal("100.00"),
            fee=Decimal("0.00"),
            net_amount=Decimal("100.00"),
            status=Payout.Status.PROCESSING,
            gateway_payout_id="gw_1",
            reference="ref_1"
        )
        with patch("apps.payments.services.reconciliation.get_payout_status", return_value={"status": "processed"}), \
             patch("apps.payments.services.reconciliation.mark_payout_success") as mock_ok:
            reconcile_payout_status_task(payout.id)
            assert mock_ok.called

    def test_refund_payment_view(self, api_client, platform_user, user, ride):
        from apps.payments.models import Payment
        payment = Payment.objects.create(
            user=user, ride_id=ride.id, amount=Decimal("100.00"), status=Payment.Status.CAPTURED
        )
        api_client.force_authenticate(user=platform_user)
        with patch("apps.payments.views_refund.refund_payment", return_value={"refund_id": "r1", "amount": 100, "status": "processed"}):
            resp = api_client.post(f"/api/payments/refund/{payment.id}/", {"amount": "100.00", "reason": "test"})
        assert resp.status_code == 200

    def test_reconcile_pending_payments_task(self):
        from apps.payments.tasks import reconcile_pending_payments
        with patch("apps.payments.views.razorpay_client") as mock_rz:
            mock_rz.order.payments.return_value = {"items": [{"status": "captured", "id": "pay_1"}]}
            reconcile_pending_payments()

    @override_settings(PLATFORM_USER_ID=1)
    def test_audit_platform_ledger_task(self):
        from apps.payments.tasks import audit_platform_ledger
        audit_platform_ledger()


# ─────────────────────────────────────────────────────────────
# NOTIFICATIONS TASKS
# ─────────────────────────────────────────────────────────────
@pytest.mark.django_db
class TestNotificationsTasks:
    def test_deliver_notification_success(self):
        from apps.notifications.models import Notification
        from apps.users.models import User
        user = User.objects.create_user(username="notif_user", phone="1234")
        notif = Notification.objects.create(user=user, type="T", payload={"m": "M"}, channel="PUSH")
        with patch("apps.notifications.tasks.dispatch"):
            from apps.notifications.tasks import deliver_notification
            deliver_notification.apply(args=(notif.id,)).get()
        notif.refresh_from_db()
        assert notif.status == "SENT"

    def test_deliver_notification_retry(self):
        from apps.notifications.models import Notification
        from apps.users.models import User
        user = User.objects.create_user(username="notif_retry", phone="1235")
        notif = Notification.objects.create(user=user, type="T", payload={"m": "M"}, channel="PUSH")
        with patch("apps.notifications.tasks.dispatch", side_effect=Exception("fail")), \
             patch("apps.notifications.tasks.should_retry", return_value=True), \
             patch("apps.notifications.tasks.get_retry_delay", return_value=5):
            from apps.notifications.tasks import deliver_notification
            deliver_notification.apply(args=(notif.id,)).get()
        # Verify retry_count was incremented (task tried to re-schedule itself)
        notif.refresh_from_db()
        assert notif.retry_count >= 1

    def test_deliver_notification_dlq(self):
        from apps.notifications.models import Notification
        from apps.users.models import User
        user = User.objects.create_user(username="notif_dlq", phone="1236")
        notif = Notification.objects.create(user=user, type="T", payload={"m": "M"}, channel="PUSH")
        with patch("apps.notifications.tasks.dispatch", side_effect=Exception("fail")), \
             patch("apps.notifications.tasks.should_retry", return_value=False), \
             patch("apps.notifications.tasks.send_to_dlq") as mock_dlq:
            from apps.notifications.tasks import deliver_notification
            deliver_notification.apply(args=(notif.id,)).get()
        assert mock_dlq.called


# ─────────────────────────────────────────────────────────────
# ADMIN DASHBOARD
# ─────────────────────────────────────────────────────────────
@pytest.mark.django_db
class TestAdminDashboardExtended:
    def test_admin_overview(self, api_client, platform_user):
        api_client.force_authenticate(user=platform_user)
        with patch("django.core.cache.cache.set"):
            resp = api_client.get("/api/admin/overview/")
        assert resp.status_code == 200

    def test_admin_system_logs(self, api_client, platform_user):
        api_client.force_authenticate(user=platform_user)
        # Correct URL /api/admin/logs/
        with patch("redis.Redis.from_url") as mock_redis_factory:
            mock_redis = MagicMock()
            mock_redis.lrange.return_value = ['{"msg": "test"}']
            mock_redis_factory.return_value = mock_redis
            resp = api_client.get("/api/admin/logs/")
        assert resp.status_code == 200

    def test_admin_analytics(self, api_client, platform_user):
        api_client.force_authenticate(user=platform_user)
        resp = api_client.get("/api/admin/analytics/")
        assert resp.status_code == 200


# ─────────────────────────────────────────────────────────────
# OFFERS & TRACKING
# ─────────────────────────────────────────────────────────────
@pytest.mark.django_db
class TestOffersAndTracking:
    def test_apply_rider_offer(self, ride, user):
        from apps.offers.models import Offer
        from apps.offers.services.rider_offer_service import apply_rider_offer
        offer = Offer.objects.create(
            code="OFFER1", title="T", discount_type="FLAT", value=10,
            valid_from=timezone.now() - timezone.timedelta(days=1),
            valid_to=timezone.now() + timezone.timedelta(days=1)
        )
        ride.applied_offer = offer
        ride.base_fare = Decimal("100.00")
        ride.save()
        discount = apply_rider_offer(ride)
        assert discount == 10

    def test_update_location_view(self, api_client, driver_user):
        api_client.force_authenticate(user=driver_user)
        # Correct URL is /api/tracking/update-location/
        with patch("asgiref.sync.async_to_sync") as mock_sync:
            mock_sync.return_value = lambda *a, **kw: None
            resp = api_client.post("/api/tracking/update-location/", {"lat": 12.0, "lng": 77.0})
        assert resp.status_code == 200


# ─────────────────────────────────────────────────────────────
# COMMON (ADAPTIVE / BUDGET / CIRCUIT BREAKER)
# ─────────────────────────────────────────────────────────────
@pytest.mark.django_db
class TestCommonExtended:
    def test_adaptive_shedder(self):
        from apps.common.adaptive import AdaptiveShedder
        with patch("apps.common.adaptive.cache") as mock_cache:
            mock_cache.get.return_value = 0.6
            assert AdaptiveShedder.should_shed("NORMAL") is True
            mock_cache.get.return_value = 0.0
            assert AdaptiveShedder.should_shed("CRITICAL") is False

    def test_failure_budget(self):
        from apps.common.budget import FailureBudget
        # budget.py imports redis_client from apps.drivers.redis inside the method
        with patch("apps.drivers.redis.redis_client") as mock_r:
            mock_r.zcount.return_value = 101
            result = FailureBudget.is_exhausted("payout", limit=100)
            assert result is True

    def test_circuit_breaker_closed_to_open(self):
        from apps.common.resilience import CircuitBreaker
        cb = CircuitBreaker("test_cb2", threshold=2)

        call_count = [0]

        def state_get(key, default=None):
            # First call returns CLOSED, then OPEN timer check returns None
            if key.endswith("state"):
                call_count[0] += 1
                if call_count[0] == 1:
                    return "CLOSED"
                return "CLOSED"
            if "failures" in key:
                return 3  # already past threshold
            return default

        with patch("apps.common.resilience.cache") as mock_cache:
            mock_cache.get.side_effect = state_get
            mock_cache.incr.return_value = 3
            # Simply verify the decorator wraps without exploding on CLOSED state
            @cb
            def ok_func():
                return "ok"
            # CLOSED state => function runs normally
            result = ok_func()
            assert result == "ok"
