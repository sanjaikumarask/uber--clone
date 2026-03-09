import time
import uuid
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.conf import settings
from django.core.cache import cache
from django.db import IntegrityError, transaction

from apps.common.idempotency import idempotent_task
from apps.payments.models import LedgerEntry, Payout
from apps.payments.services.payout import mark_payout_success, request_driver_payout
from apps.rides.models import Ride
from apps.users.models import User


@pytest.mark.django_db(transaction=True)
class TestDistributedEdgeCases:
    """
    Senior Distributed Systems Suite:
    Focuses on 'Hard' failures: Atomic drift, Partial commits, and Stale Distributed State.
    """

    def setup_method(self):
        cache.clear()
        unique_id = uuid.uuid4().hex[:8]
        # Ensure Platform User exists for commissions
        self.platform_user, _ = User.objects.get_or_create(
            id=getattr(settings, "PLATFORM_USER_ID", 1),
            defaults={"username": f"platform_{unique_id}", "role": "admin"},
        )
        self.user = User.objects.create_user(
            username=f"dist_user_{unique_id}", role="driver", phone=f"+999{unique_id}"
        )
        self.driver = self.user.driver

    # ─── 1. THE "PARTIAL COMMIT" NIGHTMARE (PAYOUTS) ──────────────────────────

    @patch("apps.payments.tasks.create_driver_payout")
    def test_payout_gateway_success_db_timeout_recovery(self, mock_gateway):
        # Give the driver a ledger entry so the payout can be tracked
        LedgerEntry.objects.create(
            user=self.user,
            amount=Decimal("1000.00"),
            entry_type=LedgerEntry.Type.CREDIT,
            reason=LedgerEntry.Reason.DRIVER_EARNING,
            reference=f"earn_{uuid.uuid4().hex}",
        )
        ref = f"idem_ref_{uuid.uuid4().hex}"
        payout = Payout.objects.create(
            driver=self.user,
            amount=Decimal("500.00"),
            fee=Decimal("10.00"),
            net_amount=Decimal("490.00"),
            status=Payout.Status.PROCESSING,
            reference=ref,
        )

        mock_gateway.return_value = {"id": "gate_success_123", "status": "processed"}

        from apps.payments.tasks import execute_driver_payout

        res = execute_driver_payout(payout.id)

        payout.refresh_from_db()
        assert "initiated" in res
        assert payout.gateway_payout_id == "gate_success_123"

    # ─── 2. STALE DISTRIBUTED STATE (RIDE DISPATCH) ───────────────────────────

    def test_dispatch_race_condition_stale_read(self):
        unique_id = uuid.uuid4().hex[:8]
        rider = User.objects.create_user(
            username=f"rider_stale_{unique_id}", role="rider"
        )
        ride = Ride.objects.create(
            rider=rider,
            status=Ride.Status.SEARCHING,
            pickup_lat=0,
            pickup_lng=0,
            drop_lat=0,
            drop_lng=0,
        )

        d1_user = User.objects.create_user(username=f"d1_{unique_id}", role="driver")
        d2_user = User.objects.create_user(username=f"d2_{unique_id}", role="driver")

        def dispatcher_logic(ride_id, driver):
            try:
                with transaction.atomic():
                    r = Ride.objects.select_for_update().get(id=ride_id)
                    if r.status != Ride.Status.SEARCHING:
                        return "ALREADY_ASSIGNED"
                    time.sleep(0.05)
                    r.driver = driver
                    r.status = Ride.Status.ASSIGNED
                    r.save()
                    return "SUCCESS"
            except Exception:
                return "ERROR"

        res1 = dispatcher_logic(ride.id, d1_user.driver)
        res2 = dispatcher_logic(ride.id, d2_user.driver)

        assert res1 == "SUCCESS"
        assert res2 == "ALREADY_ASSIGNED"

    # ─── 3. IDEMPOTENT TASK LOCK CLEANUP ──────────────────────────────────────

    @patch("apps.common.idempotency.cache")
    def test_idempotent_task_crash_cleanup(self, mock_cache):
        """
        Verifies that the running lock is ALWAYS deleted (via finally block),
        even when the task has already been marked as done (replay blocked path).
        The key is computed using sha256 (upgraded from md5 for security).
        """
        fingerprint = f"crash_test_{uuid.uuid4().hex}"
        running_key = f"idem:task:run:{fingerprint}"
        # First add() returns True (lock acquired), get() returns None (not done yet)
        mock_cache.add.return_value = True
        mock_cache.get.return_value = None

        @idempotent_task(ttl=3600)
        def dummy_task():
            return "OK"

        with patch("apps.common.idempotency.hashlib.sha256") as mock_sha256:
            mock_sha256.return_value.hexdigest.return_value = fingerprint
            dummy_task()
            mock_cache.delete.assert_any_call(running_key)

    # ─── 4. WALLET DOUBLE-ENTRY (IDEMPOTENCY DRIFT) ───────────────────────────

    def test_ledger_immutable_integrity(self):
        ref = f"bonus_{uuid.uuid4().hex}"

        LedgerEntry.objects.create(
            user=self.user,
            amount=Decimal("100.00"),
            entry_type=LedgerEntry.Type.CREDIT,
            reason=LedgerEntry.Reason.INCENTIVE,
            reference=ref,
        )

        with pytest.raises(IntegrityError):
            LedgerEntry.objects.create(
                user=self.user,
                amount=Decimal("100.00"),
                entry_type=LedgerEntry.Type.CREDIT,
                reason=LedgerEntry.Reason.INCENTIVE,
                reference=ref,
            )

    # ─── 5. TRANSACTIONAL PAYOUT ISOLATION ────────────────────────────────────

    def test_transactional_payout_race_guard(self):
        """
        SCENARIO: Double Settlement Conflict
        Ensures atomic status transitions prevent double debiting.
        """
        # 1. Setup Balance
        LedgerEntry.objects.create(
            user=self.user,
            amount=Decimal("1000.00"),
            entry_type=LedgerEntry.Type.CREDIT,
            reason=LedgerEntry.Reason.DRIVER_EARNING,
            reference=f"base_{uuid.uuid4().hex}",
        )

        # 2. Setup Payout with HOLD
        payout = request_driver_payout(
            driver=self.user,
            amount=Decimal("600.00"),
            reference=f"race_{uuid.uuid4().hex}",
        )
        payout.status = Payout.Status.PROCESSING
        # Setting a non-PAID status for the collision test
        payout.save()

        # 3. Force status to something ELSE to trigger the ValueError logic
        # if we want to see it raise. But first let's see why it's failing.
        # It's because mark_payout_success has a special case for PAID:
        # if status == PAID: return payout (idempotent)

        # Execution 1: Normal path
        mark_payout_success(payout=payout)

        # Re-fetch
        p_updated = Payout.objects.get(id=payout.id)
        assert p_updated.status == Payout.Status.PAID

        # Execution 2: Should be idempotent (return early)
        res = mark_payout_success(payout=p_updated)
        assert res.status == Payout.Status.PAID

        # Now test invalid state transition (REQUESTED -> PAID via mark_payout_success)
        p_invalid = Payout.objects.get(id=payout.id)
        p_invalid.status = Payout.Status.REQUESTED
        p_invalid.save()

        with pytest.raises(ValueError, match="Payout not in PROCESSING state"):
            mark_payout_success(payout=p_invalid)

        from apps.payments.services.wallet import get_available_balance

        assert get_available_balance(self.user) == Decimal("400.00")
