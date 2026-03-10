import pytest
from unittest.mock import patch, MagicMock
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from django.core.cache import cache
from apps.payments.tasks import trigger_scheduled_payouts, process_driver_payout, retry_failed_payouts
from apps.drivers.models import Driver
from apps.payments.models import Payout, LedgerEntry, Payment
from apps.rides.models import Ride
import apps.payments.tasks


@pytest.fixture(autouse=True)
def bypass_idempotency():
    """Prevent @idempotent_task from caching results across tests."""
    with patch("apps.common.idempotency.cache") as mock_cache:
        mock_cache.add.return_value = True   # no duplicate lock
        mock_cache.get.return_value = None   # not previously cached
        yield mock_cache


@pytest.mark.django_db
class TestPaymentTasks:
    
    @pytest.fixture
    def driver_with_balance(self, driver_user):
        driver = driver_user.driver
        # Add balance via ledger
        LedgerEntry.objects.create(
            user=driver_user,
            amount=Decimal("1000.00"),
            entry_type=LedgerEntry.Type.CREDIT,
            reason=LedgerEntry.Reason.DRIVER_EARNING
        )
        return driver

    def test_trigger_scheduled_payouts_success(self, driver_with_balance):
        with patch('apps.payments.tasks.process_driver_payout.delay') as mock_delay:
            result = trigger_scheduled_payouts()
            assert "Triggered payouts for 1 drivers" in result
            mock_delay.assert_called_once_with(driver_with_balance.id)

    def test_trigger_scheduled_payouts_fraud_blocked(self, driver_with_balance, rider_user):
        # Create a fraud flagged ride for this driver
        Ride.objects.create(
            rider=rider_user,
            driver=driver_with_balance,
            is_fraud_flagged=True,
            pickup_lat=0, pickup_lng=0, drop_lat=0, drop_lng=0,
            pickup_address="A", drop_address="B"
        )
        
        with patch('apps.payments.tasks.process_driver_payout.delay') as mock_delay:
            result = trigger_scheduled_payouts()
            assert "Triggered payouts for 0 drivers" in result
            mock_delay.assert_not_called()

    def test_trigger_scheduled_payouts_backpressure(self):
        from apps.common.backpressure import CeleryQueueGuard
        with patch.object(CeleryQueueGuard, 'can_enqueue', return_value=False):
            result = trigger_scheduled_payouts()
            assert "Shedding load due to backpressure" in result

    def test_process_driver_payout_success(self, driver_with_balance):
        driver_id = driver_with_balance.id
        
        with patch('apps.payments.tasks.create_driver_payout') as mock_gateway:
            mock_gateway.return_value = {"id": "pg_payout_123"}
            
            # Call the task function directly
            result = process_driver_payout(driver_id)
            
            assert "initiated for 1000.00" in result
            assert Payout.objects.filter(driver=driver_with_balance.user, status=Payout.Status.PROCESSING).exists()

    def test_process_driver_payout_gateway_failure(self, driver_with_balance):
        driver_id = driver_with_balance.id
        with patch('apps.payments.tasks.create_driver_payout') as mock_gateway:
            mock_gateway.side_effect = Exception("Gateway error")
            with patch('apps.payments.services.ledger.release_hold') as mock_release, \
                 patch('apps.notifications.services.alerts.send_critical_alert'):
                result = process_driver_payout(driver_id)
                assert "Payout Failed: Gateway error" in result
                payout = Payout.objects.get(driver=driver_with_balance.user)
                assert payout.status == Payout.Status.FAILED
                mock_release.assert_called_once()

    def test_process_driver_payout_unexpected_exception_retry(self, driver_with_balance):
        driver_id = driver_with_balance.id
        from apps.payments.tasks import process_driver_payout
        
        # We need to mock 'self.retry' which is available when bind=True
        # DRF/Celery bind=True means the first arg is 'self'. 
        # But here we call it as a function. 
        # Actually, in the task definition it is @shared_task(bind=True)
        
        with patch('apps.payments.tasks.get_available_balance') as mock_bal:
            mock_bal.side_effect = Exception("DB error")
            with pytest.raises(Exception) as exc:
                process_driver_payout(driver_id)
            assert "DB error" in str(exc.value)

    def test_process_driver_payout_low_balance(self, driver_user):
        # No balance
        result = process_driver_payout(driver_user.driver.id)
        assert "Skipped: Balance" in result

    def test_retry_failed_payouts_transient(self, driver_user):
        # Create a failed payout with transient error
        payout = Payout.objects.create(
            driver=driver_user,
            amount=Decimal("600.00"),
            fee=0, net_amount=600,
            status=Payout.Status.FAILED,
            reference="ref_1",
            failure_reason="Gateway Timeout (504)",
            created_at=timezone.now() - timezone.timedelta(hours=1)
        )
        # Update created_at (auto_now_add makes it hard to set via create)
        Payout.objects.filter(id=payout.id).update(created_at=timezone.now() - timezone.timedelta(hours=1))
        
        with patch('apps.payments.tasks.process_driver_payout.delay') as mock_delay:
            result = retry_failed_payouts()
            assert "Re-queued 1 transiently failed payouts" in result
            mock_delay.assert_called_once_with(driver_user.id)

    def test_reconcile_processing_payouts_success(self, driver_user):
        payout = Payout.objects.create(
            driver=driver_user,
            amount=Decimal("500.00"),
            fee=0, net_amount=500,
            status=Payout.Status.PROCESSING,
            reference="ref_2",
            gateway_payout_id="gp_123",
            updated_at=timezone.now() - timezone.timedelta(minutes=30)
        )
        # Update updated_at
        Payout.objects.filter(id=payout.id).update(updated_at=timezone.now() - timezone.timedelta(minutes=30))
        
        with patch('apps.payments.services.payout_gateway.get_payout_status') as mock_status, \
             patch('apps.payments.services.payout.mark_payout_success') as mock_success:
            mock_status.return_value = {"status": "processed"}
            result = apps.payments.tasks.reconcile_processing_payouts()
            assert "Reconciled 1 processing payouts" in result
            mock_success.assert_called_once()

    def test_audit_platform_ledger_no_drift(self):
        with patch('apps.notifications.services.alerts.send_critical_alert') as mock_alert:
            result = apps.payments.tasks.audit_platform_ledger()
            assert "Audit Completed" in result
            mock_alert.assert_not_called()

    def test_audit_platform_ledger_with_drift(self, rider_user):
        # Create a payment without ledger entry to cause drift
        Payment.objects.create(
            user=rider_user,
            ride_id=1,
            amount=Decimal("100.00"),
            status=Payment.Status.CAPTURED,
            gateway_payment_id="pay_drift"
        )
        with patch('apps.notifications.services.alerts.send_critical_alert') as mock_alert:
            result = apps.payments.tasks.audit_platform_ledger()
            assert "Audit Completed" in result # It still returns this but logs/alerts
            mock_alert.assert_called_once()
            assert "LEDGER DRIFT DETECTED" in mock_alert.call_args[1]['message']

    def test_audit_platform_ledger_exception(self):
        with patch('apps.payments.models.Payment.objects.filter') as mock_filter:
            mock_filter.side_effect = Exception("Audit system failure")
            result = apps.payments.tasks.audit_platform_ledger()
            assert "Audit system failure" in result

    def test_reconcile_pending_payments_success(self, rider_user):
        # Create a real Ride
        ride = Ride.objects.create(
            rider=rider_user,
            pickup_lat=0, pickup_lng=0, drop_lat=0, drop_lng=0,
            status=Ride.Status.COMPLETED,
            final_fare=Decimal("150.00")
        )
        payment = Payment.objects.create(
            user=rider_user,
            ride_id=ride.id,
            amount=Decimal("150.00"),
            status=Payment.Status.CREATED,
            gateway_order_id="order_1"
        )
        # Force created_at back in time to pass the 15 min cutoff
        Payment.objects.filter(id=payment.id).update(created_at=timezone.now() - timedelta(minutes=30))
        cache.clear()
        
        # Mock Razorpay
        with patch('apps.payments.views.razorpay_client') as mock_rpc:
            mock_order = MagicMock()
            mock_order.payments.return_value = {"items": [{"id": "pay_1", "status": "captured"}]}
            mock_rpc.order = mock_order
            
            with patch('apps.payments.services.payout.settle_driver_payout'):
                result = apps.payments.tasks.reconcile_pending_payments()
                assert "Reconciled 1 dropped payments" in result
                payment.refresh_from_db()
                assert payment.status == Payment.Status.CAPTURED

    def test_reconcile_pending_payments_no_gateway(self, rider_user):
        Payment.objects.create(user=rider_user, ride_id=99, amount=10, status=Payment.Status.CREATED, gateway_order_id="o1")
        with patch('apps.payments.views.razorpay_client', None):
            result = apps.payments.tasks.reconcile_pending_payments()
            assert "Gateway not configured" in result

    def test_reconcile_pending_payments_exception(self, rider_user):
        Payment.objects.create(user=rider_user, ride_id=98, amount=10, status=Payment.Status.CREATED, gateway_order_id="o2")
        with patch('apps.payments.models.Payment.objects.filter') as mock_filter:
            mock_filter.side_effect = Exception("Query error")
            result = apps.payments.tasks.reconcile_pending_payments()
            assert "Reconciliation Failed: Query error" in result
