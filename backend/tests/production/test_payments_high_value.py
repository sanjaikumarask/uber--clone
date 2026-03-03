import pytest
from unittest.mock import patch, MagicMock
from decimal import Decimal
from django.utils import timezone
from rest_framework import status
from django.db import transaction

from apps.payments.models import Payment, LedgerEntry, Payout
from apps.rides.models import Ride
from apps.users.models import User
from apps.payments.tasks import process_driver_payout, reconcile_pending_payments
from apps.payments.services.payout import settle_driver_payout

@pytest.mark.django_db
class TestPaymentsHighValue:
    """
    Principal Engineer's Payment Resilience Suite.
    Focuses on financial integrity, authorization bypass, and reconciliation.
    """

    def setup_method(self):
        self.rider = User.objects.create_user(username="rider", role="rider")
        self.driver_user = User.objects.create_user(username="driver", role="driver")
        self.driver = self.driver_user.driver
        self.ride = Ride.objects.create(
            rider=self.rider,
            driver=self.driver,
            status=Ride.Status.COMPLETED,
            final_fare=Decimal("500.00"),
            pickup_lat=0, pickup_lng=0, drop_lat=0, drop_lng=0
        )

    # --- 1. Authorization & Security ---

    @patch("apps.payments.views.razorpay_client")
    def test_verify_payment_unauthorized_hijack_attempt(self, mock_razorpay):
        """
        WHY: Prevents a malicious user from 'verifying' another person's 
        payment by passing their order_id/payment_id.
        """
        # Create a payment for Rider A
        payment = Payment.objects.create(
            user=self.rider, ride_id=self.ride.id, 
            amount=Decimal("500.00"), status=Payment.Status.CREATED,
            gateway_order_id="order_A"
        )
        
        # Malicious Rider B tries to verify Rider A's payment
        malicious_rider = User.objects.create_user(username="malicious", role="rider")
        
        from rest_framework.test import APIRequestFactory, force_authenticate
        from apps.payments.views import VerifyPaymentView
        
        factory = APIRequestFactory()
        request = factory.post("/api/v1/payments/verify/", {
            "razorpay_order_id": "order_A",
            "razorpay_payment_id": "pay_A",
            "razorpay_signature": "sig_A"
        }, format="json")
        
        force_authenticate(request, user=malicious_rider)
        view = VerifyPaymentView.as_view()
        response = view(request)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Unauthorized" in response.data["error"]

    # --- 2. Financial Integrity & Idempotency ---

    def test_settle_driver_payout_immutable_safety(self):
        """
        WHY: Ensures the driver-split logic (80/20) is idempotent.
        If called twice for the same ride, it MUST NOT double-credit the driver.
        """
        # Mock Platform User
        from django.conf import settings
        User.objects.get_or_create(id=settings.PLATFORM_USER_ID, defaults={"username": "sys_ledger"})
        
        payment = Payment.objects.create(
            user=self.rider, ride_id=self.ride.id, 
            amount=Decimal("500.00"), status=Payment.Status.CAPTURED
        )
        
        # 1. First execution
        driver_amt, plat_amt = settle_driver_payout(ride=self.ride, payment=payment)
        assert driver_amt == Decimal("400.00") # 80%
        
        # 2. Second execution (should return early without double-credit)
        driver_amt_2, plat_amt_2 = settle_driver_payout(ride=self.ride, payment=payment)
        assert driver_amt_2 == Decimal("0.00")
        
        # Verify ledger
        credits = LedgerEntry.objects.filter(ride_id=self.ride.id, entry_type=LedgerEntry.Type.CREDIT).count()
        assert credits == 2 # 1 for driver, 1 for platform

    # --- 3. Reconciliation & Recovery ---

    @patch("apps.payments.views.razorpay_client")
    def test_reconcile_pending_payments_fixes_dead_battery_scenario(self, mock_razorpay):
        """
        WHY: SLA Recovery. If a rider pays but their phone dies before 
        'VerifyPaymentView' hits our server, the system must pick it up 
        via manual reconciliation.
        """
        # Setup Platform User for Payout Settling
        from django.conf import settings
        User.objects.get_or_create(id=settings.PLATFORM_USER_ID, defaults={"username": "sys_ledger"})

        # Payment stuck in AUTHORIZED but not CAPTURED (User battery died)
        payment = Payment.objects.create(
            user=self.rider, ride_id=self.ride.id, 
            amount=Decimal("500.00"), status=Payment.Status.AUTHORIZED,
            gateway_order_id="stuck_order_123"
        )
        # Force created_at to be old (cutoff is 15 mins)
        Payment.objects.filter(id=payment.id).update(
            created_at=timezone.now() - timezone.timedelta(minutes=30)
        )
        
        # Mock Razorpay to say "Wait, I actually captured this money"
        mock_razorpay.order.payments.return_value = {
            "items": [{"id": "pay_recovered", "status": "captured"}]
        }
        
        # RUN RECONCILIATION
        reconcile_pending_payments()
        
        payment.refresh_from_db()
        assert payment.status == Payment.Status.CAPTURED
        assert payment.gateway_payment_id == "pay_recovered"
        # Verify driver was credited
        assert LedgerEntry.objects.filter(reference="earning:" + str(self.ride.id)).exists()

    # --- 4. Backpressure & Fail-over ---

    @patch("apps.payments.tasks.get_available_balance")
    @patch("apps.common.backpressure.CeleryQueueGuard.can_enqueue")
    def test_trigger_scheduled_payouts_sheds_load_on_saturation(self, mock_enqueue, mock_balance):
        """
        WHY: Prevents system lockup. If the Celery queue is already flooded 
        with 10k messages, the daily payout task must shed its load.
        """
        from apps.payments.tasks import trigger_scheduled_payouts
        
        # Simulate queue saturation
        mock_enqueue.return_value = False
        
        result = trigger_scheduled_payouts()
        assert "Shedding load" in result
        
    @patch("apps.payments.tasks.create_driver_payout")
    def test_process_driver_payout_atomic_rollback_on_failure(self, mock_gateway):
        """
        WHY: Financial consistency. If the gateway fails, internal ledger 
        HOLDs must be released immediately to avoid 'Ghost Funds'.
        """
        # Initial Credit
        LedgerEntry.objects.create(
            user=self.driver_user, amount=Decimal("1000.00"),
            entry_type=LedgerEntry.Type.CREDIT, reason=LedgerEntry.Reason.DRIVER_EARNING
        )
        
        # Force gateway rejection
        mock_gateway.side_effect = Exception("Invalid Bank Account")
        
        # Force enough balance
        mock_gateway.return_value = {"id": "gate_123"} # Not used due to side_effect
        
        process_driver_payout(self.driver.id)
        
        # Verify status is FAILED and HOLD is RELEASED
        payout = Payout.objects.get(driver=self.driver_user)
        assert payout.status == Payout.Status.FAILED
        
        from apps.payments.services.wallet import get_held_balance
        assert get_held_balance(self.driver_user) == Decimal("0.00")
