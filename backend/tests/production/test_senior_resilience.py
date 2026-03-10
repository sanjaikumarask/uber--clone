import uuid
from unittest.mock import MagicMock, patch

import pytest
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import status

from apps.drivers.models import Driver
from apps.payments.models import Payment
from apps.rides.models import Ride
from apps.rides.tasks import auto_resolve_stuck_rides
from apps.users.models import User


@pytest.mark.django_db(transaction=True)
class TestSeniorResilienceSuite:
    """
    Consolidated High-Impact Test Suite.
    Focuses on Concurrency, Atomic Drift, and Service Recovery.
    """

    def setup_method(self):
        from django.core.cache import cache

        cache.clear()

        unique_id = uuid.uuid4().hex[:6]
        self.rider = User.objects.create_user(
            username=f"rider_{unique_id}", role="rider"
        )
        self.driver_user = User.objects.create_user(
            username=f"driver_{unique_id}", role="driver"
        )
        self.driver = self.driver_user.driver
        self.driver.status = Driver.Status.ONLINE
        self.driver.save()

        # Ensure Platform User exists for commissions
        User.objects.get_or_create(
            id=settings.PLATFORM_USER_ID, defaults={"username": f"plat_{unique_id}"}
        )

    # --- 1. RIDE LICYCLE: Atomic Races ---

    @patch("apps.rides.services.matching.find_driver_and_offer_ride")
    def test_accept_ride_concurrency_with_timeout(self, mock_find):
        """
        WHY: Validates that if a driver accepts just as the timeout task runs,
        the atomic lock prevents double-transition.
        """
        ride = Ride.objects.create(
            rider=self.rider,
            driver=self.driver,
            status=Ride.Status.OFFERED,
            pickup_lat=0,
            pickup_lng=0,
            drop_lat=0,
            drop_lng=0,
        )

        from rest_framework.test import APIRequestFactory, force_authenticate

        from apps.rides.views import AcceptRideView

        factory = APIRequestFactory()
        request = factory.post(f"/api/v1/rides/{ride.id}/accept/")
        force_authenticate(request, user=self.driver_user)
        view = AcceptRideView.as_view()

        # Simulate Timeout Task running first (locking the row)
        with transaction.atomic():
            # Lock the row as the task would
            locked = Ride.objects.select_for_update().get(id=ride.id)

            # Change status in background (simulate task logic)
            locked.status = Ride.Status.SEARCHING
            locked.driver = None
            locked.save()

            # Commit occurs after block. The request should see SEARCHING
            # and fail the Accept status check.

        response = view(request, ride_id=ride.id)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "expected OFFERED" in str(response.data["error"])

    # --- 2. PAYMENTS: Financial Integrity ---

    def test_reconcile_authorized_but_not_captured(self):
        """
        WHY: Picks up 'Interrupted' payments where rider's session died after
        gateway authorization but before our server received the return call.
        """
        from apps.payments.tasks import reconcile_pending_payments

        payment = Payment.objects.create(
            user=self.rider,
            ride_id=1,
            amount=100.0,
            status=Payment.Status.AUTHORIZED,
            gateway_order_id="recon_ord_1",
        )
        # Shift back to trigger threshold
        Payment.objects.filter(id=payment.id).update(
            created_at=timezone.now() - timezone.timedelta(minutes=30)
        )

        with patch("apps.payments.views.razorpay_client") as mock_rz:
            mock_rz.order.payments.return_value = {
                "items": [{"id": "pay_xyz", "status": "captured"}]
            }

            # Setup ride for settlement
            Ride.objects.create(
                id=1,
                rider=self.rider,
                driver=self.driver,
                status=Ride.Status.COMPLETED,
                final_fare=100.0,
                pickup_lat=0,
                pickup_lng=0,
                drop_lat=0,
                drop_lng=0,
            )

            reconcile_pending_payments()

            payment.refresh_from_db()
            assert payment.status == Payment.Status.CAPTURED
            assert payment.gateway_payment_id == "pay_xyz"

    # --- 3. COMMON: SLO Enforcement ---

    @patch("apps.drivers.redis.redis_client")
    def test_slo_budget_exhaustion(self, mock_redis):
        """
        WHY: Ensures the FailureBudget correctly identifies threshold breach.
        """
        from apps.common.budget import FailureBudget

        mock_redis.zcount.return_value = 150  # Above default 100 limit

        assert FailureBudget.is_exhausted("matching_service") is True

    # --- 4. TASK IDEMPOTENCY: Collision Logic ---

    @patch("django.core.cache.cache.add")
    def test_idempotent_task_race_condition(self, mock_cache_add):
        """
        WHY: Validates that two workers won't execute the same task if
        they pick it up within the RUNNING_LOCK window.
        """
        from apps.common.idempotency import idempotent_task

        mock_cache_add.return_value = False  # Lock already exists

        handler = MagicMock(return_value="DONE")
        task = idempotent_task(ttl=3600)(handler)

        result = task(arg1="val1")
        assert result is None
        handler.assert_not_called()

    # --- 5. RIDES: Maintenance & Cleanup ---

    def test_period_cleanup_stuck_rides(self):
        """
        WHY: Ensures background hygiene doesn't destroy recently updated active state.
        """
        now = timezone.now()
        # A ride that was searching 20 mins ago, but updated 2 mins ago (e.g. searching retry)
        ride = Ride.objects.create(
            rider=self.rider,
            status=Ride.Status.SEARCHING,
            pickup_lat=0,
            pickup_lng=0,
            drop_lat=0,
            drop_lng=0,
        )
        Ride.objects.filter(id=ride.id).update(
            created_at=now - timezone.timedelta(minutes=20),
            updated_at=now - timezone.timedelta(minutes=2),
        )
        ride.refresh_from_db()

        auto_resolve_stuck_rides()

        ride.refresh_from_db()
        assert ride.status == Ride.Status.SEARCHING  # Should NOT be cancelled

        # A ride that has been SEARCHING for 20 mins and is TRULY abandoned
        ride2 = Ride.objects.create(
            rider=self.rider,
            status=Ride.Status.SEARCHING,
            pickup_lat=0,
            pickup_lng=0,
            drop_lat=0,
            drop_lng=0,
        )
        Ride.objects.filter(id=ride2.id).update(
            created_at=now - timezone.timedelta(minutes=20),
            updated_at=now - timezone.timedelta(minutes=20),
        )
        ride2.refresh_from_db()

        auto_resolve_stuck_rides()
        ride2.refresh_from_db()
        assert ride2.status == Ride.Status.CANCELLED
