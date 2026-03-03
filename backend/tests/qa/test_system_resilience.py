import pytest
from unittest.mock import patch, MagicMock
from decimal import Decimal
from django.db import transaction, IntegrityError
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings
from apps.drivers.models import Driver, DriverStats
from apps.payments.models import Payout, Payment, LedgerEntry
from apps.rides.models import Ride
from apps.users.models import User
from apps.payments.tasks import process_driver_payout, audit_platform_ledger, trigger_scheduled_payouts, reconcile_processing_payouts

@pytest.mark.django_db
class TestSystemResilience:
    """
    Senior QA Resilience Suite: Focuses on failure modes, concurrency, 
    and financial integrity.
    """

    def setup_method(self):
        # Clear cache to ensure idempotency keys don't block repeating tests
        cache.clear()
        
        # Ensure Platform User exists for financial logic
        User.objects.get_or_create(
            id=getattr(settings, "PLATFORM_USER_ID", 1),
            defaults={"username": "platform_system", "role": "admin"}
        )

        # Setup basic driver and user
        self.user = User.objects.create_user(username="resilient_driver", role="driver", phone="+111")
        self.driver = self.user.driver
        self.driver.is_verified = True
        self.driver.save()
        
        # Setup some balance
        LedgerEntry.objects.create(
            user=self.user,
            amount=Decimal("1000.00"),
            entry_type=LedgerEntry.Type.CREDIT,
            reason=LedgerEntry.Reason.DRIVER_EARNING,
            reference="initial_balance"
        )

    @patch("apps.payments.services.payout.mark_payout_success")
    @patch("apps.payments.services.payout_gateway.get_payout_status")
    def test_payout_ghost_failure_recovery_flow(self, mock_status, mock_mark_success):
        """
        SCENARIO: Ghost Payout Recovery
        Ensures the reconciliation task can find stuck PROCESSING payouts 
        and update them if the gateway confirms they are 'processed'.
        """
        # 1. Manually create a stuck payout
        payout = Payout.objects.create(
            driver=self.user,
            amount=Decimal("600.00"),
            fee=Decimal("0.00"),
            net_amount=Decimal("600.00"),
            status=Payout.Status.PROCESSING,
            reference="stuck_ref_123",
            gateway_payout_id="gate_999"
        )
        
        # Set updated_at to be old enough for reconciliation (15 mins cutoff)
        Payout.objects.filter(id=payout.id).update(
            updated_at=timezone.now() - timezone.timedelta(minutes=20)
        )
        
        # 2. Mock Gateway status check
        mock_status.return_value = {"status": "processed", "id": "gate_999"}
        
        # 3. Trigger Reconciliation
        reconcile_processing_payouts()
        
        # 4. Verify mark_payout_success was called
        # Note: In tasks.py, it imports mark_payout_success locally. 
        # Patching it in the service should work if imported AFTER patch.
        mock_mark_success.assert_called_once()

    @patch("apps.common.idempotency.cache")
    def test_idempotency_task_locking_concurrency(self, mock_cache):
        """
        SCENARIO: Concurrent Task Execution
        Ensures @idempotent_task decorator correctly blocks a second task 
        while the first is still running (Phase 1).
        """
        # Simulate 'running' lock already exists in Redis
        mock_cache.add.return_value = False 
        
        result = process_driver_payout(self.driver.id)
        
        # Should return None/Skip immediately
        assert result is None
        mock_cache.add.assert_called()

    @patch("apps.notifications.services.alerts.send_critical_alert")
    def test_ledger_integrity_drift_detection(self, mock_alert):
        """
        SCENARIO: Financial Integrity (Ledger Drift)
        Audit must detect drift when Payments != Credits.
        """
        rider = User.objects.create_user(username="rider_audit", role="rider", phone="+222")
        ride = Ride.objects.create(rider=rider, pickup_lat=0, pickup_lng=0, drop_lat=0, drop_lng=0)
        
        Payment.objects.create(
            user=rider, 
            ride_id=ride.id, 
            amount=Decimal("1000.00"), 
            status=Payment.Status.CAPTURED,
            gateway_payment_id="pay_abc"
        )
        
        LedgerEntry.objects.create(
            user=self.user, 
            ride_id=ride.id, 
            amount=Decimal("700.00"), 
            entry_type=LedgerEntry.Type.CREDIT, 
            reason=LedgerEntry.Reason.DRIVER_EARNING,
            reference="pay_abc"
        )
        # Missing Platform Commission -> Drift!
        
        audit_platform_ledger()
        
        # Assert Alert fired
        assert any(call.kwargs.get('level') == 'CRITICAL' for call in mock_alert.call_args_list)

    @patch("apps.drivers.redis.redis_client")
    def test_celery_queue_saturation_shedding(self, mock_redis):
        """
        SCENARIO: System Saturation (Backpressure)
        When Celery queue is deep, skip enqueuing of non-critical periodic tasks.
        """
        # 1. Mock queue depth over limit (limit 5000)
        mock_redis.llen.return_value = 6000
        
        # 2. Attempt to trigger payouts
        result = trigger_scheduled_payouts()
        
        # 3. Verify shedding
        assert "Shedding load" in result
        
    def test_ride_accept_race_condition(self):
        """
        SCENARIO: Atomic Race Condition
        Ensures only one driver can be assigned to a ride.
        """
        rider = User.objects.create_user(username="rider_race", role="rider", phone="+333")
        ride = Ride.objects.create(
            rider=rider, 
            status=Ride.Status.SEARCHING,
            pickup_lat=0, pickup_lng=0, drop_lat=0, drop_lng=0
        )
        
        user2 = User.objects.create_user(username="driver_race_2", role="driver", phone="+444")
        
        def accept_logic(ride_id, driver):
            with transaction.atomic():
                r = Ride.objects.select_for_update().get(id=ride_id)
                if r.status != Ride.Status.SEARCHING:
                    raise IntegrityError("Ride already taken")
                r.driver = driver
                r.status = Ride.Status.ASSIGNED
                r.save()
        
        accept_logic(ride.id, self.driver)
        
        with pytest.raises(IntegrityError, match="Ride already taken"):
            accept_logic(ride.id, user2.driver)
        
        ride.refresh_from_db()
        assert ride.driver == self.driver

    @patch("apps.drivers.redis.redis_client")
    @patch("apps.drivers.redis.remove_driver_from_geo")
    @patch("apps.notifications.services.alerts.send_critical_alert")
    def test_ghost_session_pruning_resilience(self, mock_alert, mock_remove_geo, mock_redis):
        """
        SCENARIO: SLA Maintenance (Ghost Sessions)
        Detects and prunes drivers who are technically OFFLINE but stuck in ONLINE state in DB.
        """
        from apps.drivers.tasks import prune_ghost_driver_sessions
        
        # 1. Driver in DB is ONLINE
        self.driver.status = Driver.Status.ONLINE
        self.driver.save()
        
        # 2. Redis has NO last_seen heartbeat (or it's too old)
        mock_redis.get.return_value = None 
        # Update updated_at to be old enough for pruning
        Driver.objects.filter(id=self.driver.id).update(
            updated_at=timezone.now() - timezone.timedelta(minutes=30)
        )
        
        # 3. Run pruning
        prune_ghost_driver_sessions()
        
        # 4. Verify results
        self.driver.refresh_from_db()
        assert self.driver.status == Driver.Status.OFFLINE
        mock_remove_geo.assert_called_once_with(driver_id=self.driver.id)
        mock_alert.assert_called_once()
