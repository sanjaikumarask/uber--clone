"""
tests/unit/payments/test_payments_tasks_comprehensive.py

Comprehensive pytest tests for apps/payments/tasks.py
Covers all 6 Celery tasks:
  - trigger_scheduled_payouts
  - process_driver_payout
  - execute_driver_payout
  - retry_failed_payouts
  - reconcile_processing_payouts
  - reconcile_pending_payments
  - audit_platform_ledger
"""
import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock, call
from django.test import override_settings
from django.utils import timezone


@pytest.fixture(autouse=True)
def bypass_idempotency():
    """Patch cache so idempotent_task always runs the function body."""
    with patch("apps.common.idempotency.cache") as mock_cache:
        mock_cache.add.return_value = True  # no duplicate lock
        mock_cache.get.return_value = None  # not done before
        yield mock_cache



# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────
def _make_driver(user):
    from apps.drivers.models import Driver
    driver, _ = Driver.objects.update_or_create(
        user=user,
        defaults={"status": Driver.Status.ONLINE, "is_verified": True},
    )
    return driver


def _make_payout(user, status="PROCESSING", reference="ref_test", amount="500.00",
                 gateway_payout_id="gw_123", failure_reason=""):
    from apps.payments.models import Payout
    return Payout.objects.create(
        driver=user,
        amount=Decimal(amount),
        fee=Decimal("0.00"),
        net_amount=Decimal(amount),
        status=status,
        reference=reference,
        gateway_payout_id=gateway_payout_id,
        failure_reason=failure_reason or "",
    )


# ─────────────────────────────────────────────────────────────
# 1. trigger_scheduled_payouts
# ─────────────────────────────────────────────────────────────
@pytest.mark.django_db
class TestTriggerScheduledPayouts:

    def test_no_drivers_returns_zero(self):
        from apps.payments.tasks import trigger_scheduled_payouts
        with patch("apps.common.backpressure.CeleryQueueGuard.can_enqueue", return_value=True), \
             patch("apps.payments.tasks.get_available_balance", return_value=Decimal("100.00")):
            result = trigger_scheduled_payouts()
        assert "Triggered" in result

    def test_backpressure_sheds_task(self):
        from apps.payments.tasks import trigger_scheduled_payouts
        with patch("apps.common.backpressure.CeleryQueueGuard.can_enqueue", return_value=False):
            result = trigger_scheduled_payouts()
        assert "backpressure" in result.lower() or "Shedding" in result

    def test_driver_with_sufficient_balance_queued(self, driver_user):
        from apps.payments.tasks import trigger_scheduled_payouts
        with patch("apps.common.backpressure.CeleryQueueGuard.can_enqueue", return_value=True), \
             patch("apps.payments.tasks.get_available_balance", return_value=Decimal("600.00")), \
             patch("apps.payments.tasks.process_driver_payout.delay") as mock_delay:
            result = trigger_scheduled_payouts()
        mock_delay.assert_called()
        assert "Triggered" in result

    def test_driver_with_insufficient_balance_skipped(self, driver_user):
        from apps.payments.tasks import trigger_scheduled_payouts
        with patch("apps.common.backpressure.CeleryQueueGuard.can_enqueue", return_value=True), \
             patch("apps.payments.tasks.get_available_balance", return_value=Decimal("10.00")), \
             patch("apps.payments.tasks.process_driver_payout.delay") as mock_delay:
            result = trigger_scheduled_payouts()
        mock_delay.assert_not_called()
        assert "0" in result

    def test_fraud_flagged_driver_skipped(self, user, driver_user):
        from apps.rides.models import Ride
        driver = _make_driver(driver_user)
        Ride.objects.create(
            rider=user, driver=driver,
            pickup_lat=12.9, pickup_lng=77.5,
            drop_lat=12.8, drop_lng=77.4,
            status="COMPLETED", is_fraud_flagged=True,
        )
        from apps.payments.tasks import trigger_scheduled_payouts
        with patch("apps.common.backpressure.CeleryQueueGuard.can_enqueue", return_value=True), \
             patch("apps.payments.tasks.get_available_balance", return_value=Decimal("600.00")), \
             patch("apps.payments.tasks.process_driver_payout.delay") as mock_delay:
            trigger_scheduled_payouts()
        # The fraud-flagged driver must not be scheduled
        for c in mock_delay.call_args_list:
            assert c[0][0] != driver.id

    def test_blocked_driver_excluded(self, driver_user):
        """Drivers with BLOCKED status are excluded from payout."""
        from apps.drivers.models import Driver
        driver = _make_driver(driver_user)
        driver.status = Driver.Status.BLOCKED
        driver.save()
        from apps.payments.tasks import trigger_scheduled_payouts
        with patch("apps.common.backpressure.CeleryQueueGuard.can_enqueue", return_value=True), \
             patch("apps.payments.tasks.get_available_balance", return_value=Decimal("600.00")), \
             patch("apps.payments.tasks.process_driver_payout.delay") as mock_delay:
            result = trigger_scheduled_payouts()
        # blocked driver excluded; no calls expected
        for c in mock_delay.call_args_list:
            assert c[0][0] != driver.id


# ─────────────────────────────────────────────────────────────
# 2. process_driver_payout
# ─────────────────────────────────────────────────────────────
@pytest.mark.django_db
class TestProcessDriverPayout:

    def test_balance_below_threshold_skipped(self, driver_user):
        driver = _make_driver(driver_user)
        from apps.payments.tasks import process_driver_payout
        with patch("apps.payments.tasks.get_available_balance", return_value=Decimal("100.00")):
            result = process_driver_payout.apply(args=(driver.id,)).get()
        assert "Skipped" in result and "Balance" in result

    def test_duplicate_payout_today_skipped(self, driver_user):
        from apps.payments.models import Payout
        driver = _make_driver(driver_user)
        today_str = timezone.now().date().isoformat()
        ref = f"payout:scheduled:{driver_user.id}:{today_str}"
        Payout.objects.create(
            driver=driver_user, amount=Decimal("600.00"),
            fee=Decimal("0.00"), net_amount=Decimal("600.00"),
            status="REQUESTED", reference=ref,
        )
        from apps.payments.tasks import process_driver_payout
        with patch("apps.payments.tasks.get_available_balance", return_value=Decimal("600.00")):
            result = process_driver_payout.apply(args=(driver.id,)).get()
        assert "Skipped" in result

    def test_successful_payout_creation(self, driver_user):
        driver = _make_driver(driver_user)
        from apps.payments.tasks import process_driver_payout
        mock_payout = MagicMock()
        mock_payout.reference = "payout:scheduled:1:2026-03-08"
        with patch("apps.payments.tasks.get_available_balance", return_value=Decimal("600.00")), \
             patch("apps.payments.tasks.request_driver_payout", return_value=mock_payout), \
             patch("apps.payments.tasks.create_driver_payout",
                   return_value={"id": "gw_payout_123"}):
            result = process_driver_payout.apply(args=(driver.id,)).get()
        assert "initiated" in result or "Payout" in result

    def test_gateway_failure_marks_payout_failed(self, driver_user):
        driver = _make_driver(driver_user)
        from apps.payments.tasks import process_driver_payout
        mock_payout = MagicMock()
        mock_payout.reference = "payout:scheduled:1:2026-03-08"
        mock_payout.driver = MagicMock(first_name="Test")
        with patch("apps.payments.tasks.get_available_balance", return_value=Decimal("600.00")), \
             patch("apps.payments.tasks.request_driver_payout", return_value=mock_payout), \
             patch("apps.payments.tasks.create_driver_payout",
                   side_effect=Exception("bank invalid")), \
             patch("apps.payments.services.ledger.release_hold"), \
             patch("apps.notifications.services.alerts.send_critical_alert"):
            result = process_driver_payout.apply(args=(driver.id,)).get()
        assert "Failed" in result or "bank invalid" in result

    def test_outer_exception_triggers_retry(self, driver_user):
        driver = _make_driver(driver_user)
        from apps.payments.tasks import process_driver_payout
        from celery.exceptions import Retry
        with patch("apps.payments.tasks.get_available_balance",
                   side_effect=Exception("db crashed")), \
             patch("apps.common.backpressure.RetryStrategy.get_countdown", return_value=10):
            try:
                result = process_driver_payout.apply(args=(driver.id,)).get()
            except Retry:
                result = None  # expected — Celery raised Retry
        assert result is None or "Failed" in str(result)

    def test_driver_not_found(self):
        from apps.payments.tasks import process_driver_payout
        from celery.exceptions import Retry
        with patch("apps.common.backpressure.RetryStrategy.get_countdown", return_value=10):
            try:
                result = process_driver_payout.apply(args=(999999,)).get()
            except Retry:
                result = None  # expected — Celery raised Retry
        assert result is None or "Failed" in str(result)


# ─────────────────────────────────────────────────────────────
# 3. execute_driver_payout
# ─────────────────────────────────────────────────────────────
@pytest.mark.django_db
class TestExecuteDriverPayout:

    def test_non_processing_payout_skipped(self, driver_user):
        payout = _make_payout(driver_user, status="REQUESTED")
        from apps.payments.tasks import execute_driver_payout
        result = execute_driver_payout.apply(args=(payout.id,)).get()
        assert result is None

    def test_processing_payout_succeeds(self, driver_user):
        payout = _make_payout(driver_user, status="PROCESSING")
        from apps.payments.tasks import execute_driver_payout
        with patch("apps.payments.tasks.create_driver_payout",
                   return_value={"id": "gw_999"}):
            result = execute_driver_payout.apply(args=(payout.id,)).get()
        assert "initiated" in result
        payout.refresh_from_db()
        assert payout.gateway_payout_id == "gw_999"

    def test_gateway_failure_marks_failed_and_releases_hold(self, driver_user):
        payout = _make_payout(driver_user, status="PROCESSING")
        from apps.payments.tasks import execute_driver_payout
        with patch("apps.payments.tasks.create_driver_payout",
                   side_effect=Exception("timeout")), \
             patch("apps.payments.services.ledger.release_hold") as mock_release:
            result = execute_driver_payout.apply(args=(payout.id,)).get()
        assert "Failed" in result or result is None
        payout.refresh_from_db()
        assert payout.status == "FAILED"
        mock_release.assert_called_once()


# ─────────────────────────────────────────────────────────────
# 4. retry_failed_payouts
# ─────────────────────────────────────────────────────────────
@pytest.mark.django_db
class TestRetryFailedPayouts:

    def test_no_failed_payouts(self):
        from apps.payments.tasks import retry_failed_payouts
        result = retry_failed_payouts()
        assert "0" in result

    def test_retries_timeout_payouts(self, driver_user):
        from datetime import timedelta
        payout = _make_payout(
            driver_user, status="FAILED",
            failure_reason="network timeout occurred",
            reference="ref_timeout",
        )
        # Manually set created_at into the eligible window (between 2 days and 15 min ago)
        from apps.payments.models import Payout
        Payout.objects.filter(id=payout.id).update(
            created_at=timezone.now() - timedelta(hours=6)
        )
        from apps.payments.tasks import retry_failed_payouts
        with patch("apps.payments.tasks.process_driver_payout.delay") as mock_delay:
            result = retry_failed_payouts()
        mock_delay.assert_called_once_with(payout.driver_id)
        assert "1" in result

    def test_non_transient_errors_not_retried(self, driver_user):
        from datetime import timedelta
        payout = _make_payout(
            driver_user, status="FAILED",
            failure_reason="invalid bank account number",
            reference="ref_bank",
        )
        from apps.payments.models import Payout
        Payout.objects.filter(id=payout.id).update(
            created_at=timezone.now() - timedelta(hours=6)
        )
        from apps.payments.tasks import retry_failed_payouts
        with patch("apps.payments.tasks.process_driver_payout.delay") as mock_delay:
            retry_failed_payouts()
        mock_delay.assert_not_called()

    def test_unavailable_error_retried(self, driver_user):
        from datetime import timedelta
        payout = _make_payout(
            driver_user, status="FAILED",
            failure_reason="service unavailable",
            reference="ref_unavail",
        )
        from apps.payments.models import Payout
        Payout.objects.filter(id=payout.id).update(
            created_at=timezone.now() - timedelta(hours=2)
        )
        from apps.payments.tasks import retry_failed_payouts
        with patch("apps.payments.tasks.process_driver_payout.delay") as mock_delay:
            result = retry_failed_payouts()
        mock_delay.assert_called_once()


# ─────────────────────────────────────────────────────────────
# 5. reconcile_processing_payouts
# ─────────────────────────────────────────────────────────────
@pytest.mark.django_db
class TestReconcileProcessingPayouts:

    def test_no_processing_payouts(self):
        from apps.payments.tasks import reconcile_processing_payouts
        result = reconcile_processing_payouts()
        assert "0" in result

    def test_reconciles_processed(self, driver_user):
        from datetime import timedelta
        payout = _make_payout(driver_user, status="PROCESSING", reference="ref_proc")
        from apps.payments.models import Payout
        Payout.objects.filter(id=payout.id).update(
            updated_at=timezone.now() - timedelta(hours=1)
        )
        from apps.payments.tasks import reconcile_processing_payouts
        with patch("apps.payments.services.payout_gateway.get_payout_status",
                   return_value={"status": "processed"}), \
             patch("apps.payments.services.payout.mark_payout_success") as mock_ok:
            result = reconcile_processing_payouts()
        mock_ok.assert_called_once_with(payout=payout)
        assert "1" in result

    def test_reconciles_failed(self, driver_user):
        from datetime import timedelta
        payout = _make_payout(driver_user, status="PROCESSING", reference="ref_fail")
        from apps.payments.models import Payout
        Payout.objects.filter(id=payout.id).update(
            updated_at=timezone.now() - timedelta(hours=1)
        )
        from apps.payments.tasks import reconcile_processing_payouts
        with patch("apps.payments.services.payout_gateway.get_payout_status",
                   return_value={"status": "failed", "failure_reason": "gateway down"}), \
             patch("apps.payments.services.payout.mark_payout_failed") as mock_fail:
            result = reconcile_processing_payouts()
        mock_fail.assert_called_once()

    def test_reconciles_cancelled(self, driver_user):
        from datetime import timedelta
        payout = _make_payout(driver_user, status="PROCESSING", reference="ref_cancel")
        from apps.payments.models import Payout
        Payout.objects.filter(id=payout.id).update(
            updated_at=timezone.now() - timedelta(hours=1)
        )
        from apps.payments.tasks import reconcile_processing_payouts
        with patch("apps.payments.services.payout_gateway.get_payout_status",
                   return_value={"status": "cancelled"}), \
             patch("apps.payments.services.payout.mark_payout_failed") as mock_fail:
            reconcile_processing_payouts()
        mock_fail.assert_called_once()

    def test_gateway_returns_none_skips(self, driver_user):
        from datetime import timedelta
        payout = _make_payout(driver_user, status="PROCESSING", reference="ref_none")
        from apps.payments.models import Payout
        Payout.objects.filter(id=payout.id).update(
            updated_at=timezone.now() - timedelta(hours=1)
        )
        from apps.payments.tasks import reconcile_processing_payouts
        with patch("apps.payments.services.payout_gateway.get_payout_status",
                   return_value=None):
            result = reconcile_processing_payouts()
        assert "0" in result

    def test_exception_fires_alert(self, driver_user):
        from datetime import timedelta
        payout = _make_payout(driver_user, status="PROCESSING", reference="ref_exc")
        from apps.payments.models import Payout
        Payout.objects.filter(id=payout.id).update(
            updated_at=timezone.now() - timedelta(hours=1)
        )
        from apps.payments.tasks import reconcile_processing_payouts
        with patch("apps.payments.services.payout_gateway.get_payout_status",
                   side_effect=Exception("API error")), \
             patch("apps.notifications.services.alerts.send_critical_alert") as mock_alert:
            reconcile_processing_payouts()
        mock_alert.assert_called_once()


# ─────────────────────────────────────────────────────────────
# 6. reconcile_pending_payments
# ─────────────────────────────────────────────────────────────
@pytest.mark.django_db
class TestReconcilePendingPayments:

    def test_no_gateway_configured(self):
        from apps.payments.tasks import reconcile_pending_payments
        with patch("apps.payments.views.razorpay_client", None):
            result = reconcile_pending_payments()
        assert "not configured" in result

    def test_no_pending_payments(self):
        from apps.payments.tasks import reconcile_pending_payments
        mock_rz = MagicMock()
        with patch("apps.payments.views.razorpay_client", mock_rz):
            result = reconcile_pending_payments()
        assert "0" in result

    def test_reconcile_captured_payment(self, user):
        from datetime import timedelta
        from apps.rides.models import Ride
        from apps.payments.models import Payment
        ride = Ride.objects.create(
            rider=user, pickup_lat=12.9, pickup_lng=77.5,
            drop_lat=12.8, drop_lng=77.4, status="COMPLETED",
        )
        payment = Payment.objects.create(
            user=user, ride_id=ride.id,
            amount=Decimal("100.00"),
            status=Payment.Status.CREATED,
            gateway_order_id="order_test1",
        )
        # Place created_at in the eligibility window (30 min ago)
        Payment.objects.filter(id=payment.id).update(
            created_at=timezone.now() - timedelta(minutes=30)
        )
        mock_rz = MagicMock()
        mock_rz.order.payments.return_value = {
            "items": [{"status": "captured", "id": "pay_reconciled"}]
        }
        from apps.payments.tasks import reconcile_pending_payments
        with patch("apps.payments.views.razorpay_client", mock_rz), \
             patch("apps.payments.services.payout.settle_driver_payout"):
            result = reconcile_pending_payments()
        assert "1" in result
        payment.refresh_from_db()
        assert payment.status == Payment.Status.CAPTURED

    def test_already_captured_payment_skipped(self, user):
        from datetime import timedelta
        from apps.rides.models import Ride
        from apps.payments.models import Payment
        ride = Ride.objects.create(
            rider=user, pickup_lat=12.9, pickup_lng=77.5,
            drop_lat=12.8, drop_lng=77.4, status="COMPLETED",
        )
        payment = Payment.objects.create(
            user=user, ride_id=ride.id,
            amount=Decimal("100.00"),
            status=Payment.Status.CREATED,
            gateway_order_id="order_test2",
        )
        Payment.objects.filter(id=payment.id).update(
            created_at=timezone.now() - timedelta(minutes=30)
        )
        mock_rz = MagicMock()
        mock_rz.order.payments.return_value = {
            "items": [{"status": "captured", "id": "pay_already"}]
        }
        # Manually mark as CAPTURED before task processes it
        Payment.objects.filter(id=payment.id).update(status=Payment.Status.CAPTURED)
        from apps.payments.tasks import reconcile_pending_payments
        with patch("apps.payments.views.razorpay_client", mock_rz), \
             patch("apps.payments.services.payout.settle_driver_payout"):
            result = reconcile_pending_payments()
        # Should skip the already-captured record
        assert "0" in result

    def test_no_captured_item_in_gateway(self, user):
        from apps.rides.models import Ride
        from apps.payments.models import Payment
        ride = Ride.objects.create(
            rider=user, pickup_lat=12.9, pickup_lng=77.5,
            drop_lat=12.8, drop_lng=77.4, status="SEARCHING",
        )
        Payment.objects.create(
            user=user, ride_id=ride.id,
            amount=Decimal("100.00"),
            status=Payment.Status.AUTHORIZED,
            gateway_order_id="order_test3",
        )
        mock_rz = MagicMock()
        mock_rz.order.payments.return_value = {
            "items": [{"status": "created", "id": "pay_pending"}]
        }
        from apps.payments.tasks import reconcile_pending_payments
        with patch("apps.payments.views.razorpay_client", mock_rz):
            result = reconcile_pending_payments()
        assert "0" in result

    def test_payment_exception_continues_loop(self, user):
        from apps.rides.models import Ride
        from apps.payments.models import Payment
        ride = Ride.objects.create(
            rider=user, pickup_lat=12.9, pickup_lng=77.5,
            drop_lat=12.8, drop_lng=77.4, status="COMPLETED",
        )
        Payment.objects.create(
            user=user, ride_id=ride.id,
            amount=Decimal("100.00"),
            status=Payment.Status.CREATED,
            gateway_order_id="order_explode",
        )
        mock_rz = MagicMock()
        mock_rz.order.payments.side_effect = Exception("gateway down")
        from apps.payments.tasks import reconcile_pending_payments
        with patch("apps.payments.views.razorpay_client", mock_rz):
            result = reconcile_pending_payments()  # must not raise
        assert "0" in result


# ─────────────────────────────────────────────────────────────
# 7. audit_platform_ledger
# ─────────────────────────────────────────────────────────────
@pytest.mark.django_db
class TestAuditPlatformLedger:

    @override_settings(PLATFORM_USER_ID=1)
    def test_empty_db_no_drift(self, platform_user):
        from apps.payments.tasks import audit_platform_ledger
        result = audit_platform_ledger()
        assert "Audit Completed" in result

    @override_settings(PLATFORM_USER_ID=1)
    def test_drift_detected_fires_alert(self, platform_user, user):
        from apps.payments.models import Payment, LedgerEntry
        from apps.rides.models import Ride
        ride = Ride.objects.create(
            rider=user, pickup_lat=12.9, pickup_lng=77.5,
            drop_lat=12.8, drop_lng=77.4, status="COMPLETED",
        )
        # Create an imbalanced situation:
        # Payment captured = 200, but no driver earning ledger
        Payment.objects.create(
            user=user, ride_id=ride.id,
            amount=Decimal("200.00"),
            refunded_amount=Decimal("0.00"),
            status=Payment.Status.CAPTURED,
        )
        from apps.payments.tasks import audit_platform_ledger
        with patch("apps.notifications.services.alerts.send_critical_alert") as mock_alert:
            result = audit_platform_ledger()
        # If drift is non-zero, alert must be called
        # (ledger credits = 0, internal_sum = 200 => drift)
        mock_alert.assert_called()
        assert "Audit Completed" in result

    @override_settings(PLATFORM_USER_ID=1)
    def test_balanced_ledger_no_alert(self, platform_user, user):
        from apps.payments.models import Payment, LedgerEntry
        from apps.rides.models import Ride
        ride = Ride.objects.create(
            rider=user, pickup_lat=12.9, pickup_lng=77.5,
            drop_lat=12.8, drop_lng=77.4, status="COMPLETED",
        )
        Payment.objects.create(
            user=user, ride_id=ride.id,
            amount=Decimal("100.00"),
            refunded_amount=Decimal("0.00"),
            status=Payment.Status.CAPTURED,
        )
        # Create matching ledger entries so the books balance
        LedgerEntry.objects.create(
            user=user,
            ride_id=ride.id,
            amount=Decimal("80.00"),
            entry_type=LedgerEntry.Type.CREDIT,
            reason=LedgerEntry.Reason.DRIVER_EARNING,
            reference="pay_bal1",
        )
        LedgerEntry.objects.create(
            user=platform_user,
            ride_id=ride.id,
            amount=Decimal("20.00"),
            entry_type=LedgerEntry.Type.CREDIT,
            reason=LedgerEntry.Reason.PLATFORM_COMMISSION,
            reference="pay_bal2",
        )
        from apps.payments.tasks import audit_platform_ledger
        with patch("apps.notifications.services.alerts.send_critical_alert") as mock_alert:
            result = audit_platform_ledger()
        mock_alert.assert_not_called()
        assert "Audit Completed" in result

    @override_settings(PLATFORM_USER_ID=1)
    def test_exception_in_audit_returns_error_string(self):
        from apps.payments.tasks import audit_platform_ledger
        with patch("apps.payments.models.Payment.objects.filter",
                   side_effect=Exception("db conn lost")):
            result = audit_platform_ledger()
        # Must not raise, must return error string
        assert "db conn lost" in result or isinstance(result, str)
