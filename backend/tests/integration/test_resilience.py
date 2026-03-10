from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from apps.common.circuit_breaker import CircuitOpenError
from apps.payments.services.payout_gateway import create_driver_payout


@pytest.mark.django_db
class TestSystemResilience:
    """
    Verification of 'Self-Healing' and 'Fail-Fast' patterns:
    - Circuit Breaker performance under external API failure
    - Database transaction integrity under partial crash
    - Idempotency consistency
    """

    def test_razorpay_circuit_breaker_trip(self):
        """
        Verify that multiple external API failures trip the circuit breaker.
        Prevents cascading failure and resource exhaustion.
        """
        # Mock payout object
        mock_payout = MagicMock()
        mock_payout.driver.get_full_name.return_value = "Test Driver"

        # 1. Force 5 failures to hit the threshold
        with patch("apps.payments.services.payout_gateway.client.post") as mock_post:
            mock_post.side_effect = Exception("Razorpay 500 Internal Error")

            for _ in range(5):
                try:
                    create_driver_payout(payout=mock_payout)
                except Exception:
                    pass

            # 2. The 6th attempt should NOT even call the mock (fast-fail)
            # It should raise CircuitOpenError
            with pytest.raises(CircuitOpenError):
                create_driver_payout(payout=mock_payout)

            # Verify mock was only called 5 times, not 6
            assert mock_post.call_count == 5

    def test_idempotent_task_replay_safety(self, db):
        """
        Verify that @idempotent_task prevents double execution of critical financial tasks.
        """
        from apps.common.idempotency import idempotent_task

        execution_log = []

        @idempotent_task(ttl=60)
        def process_payout(payout_id):
            execution_log.append(payout_id)
            return f"Processed {payout_id}"

        # 1. First execution
        res1 = process_payout("REF-123")
        assert res1 == "Processed REF-123"
        assert len(execution_log) == 1

        # 2. Replay (Retry storm)
        res2 = process_payout("REF-123")
        assert res2 is None  # Decorator returns None for replayed tasks
        assert len(execution_log) == 1  # Work body MUST NOT run twice

    def test_payout_rollback_on_failure(self, driver_user):
        """
        Verify that if the gateway call fails, the Ledger HOLD is rolled back.
        Uses real transaction.atomic logic from tasks.py.
        """
        from apps.payments.models import LedgerEntry, Payout
        from apps.payments.tasks import process_driver_payout

        # Setup: Give driver some balance
        LedgerEntry.objects.create(
            user=driver_user,
            amount=1000,
            entry_type=LedgerEntry.Type.CREDIT,
            reason=LedgerEntry.Type.CREDIT,
        )

        # 1. Mock gateway to CRASH
        with patch("apps.payments.tasks.create_driver_payout") as mock_gateway:
            mock_gateway.side_effect = RuntimeError("Fatal Gateway Error")

            # 2. Run the task
            try:
                # We call it synchronously to ensure the exception bubbles if not caught
                process_driver_payout(driver_user.driver.id)
            except RuntimeError:
                pass

            # 3. Assert functional FAILURE state (Audit friendly)
            payout = Payout.objects.get(
                driver=driver_user,
                reference=f"payout:scheduled:{driver_user.id}:{timezone.now().date().isoformat()}",
            )
            assert payout.status == Payout.Status.FAILED
            assert "Fatal Gateway Error" in payout.failure_reason

            # Verify Ledger has HOLD and RELEASE
            holds = LedgerEntry.objects.filter(
                user=driver_user, entry_type=LedgerEntry.Type.HOLD
            )
            releases = LedgerEntry.objects.filter(
                user=driver_user, entry_type=LedgerEntry.Type.RELEASE
            )

            assert holds.exists()
            assert releases.exists()
            assert holds.first().amount == releases.first().amount
