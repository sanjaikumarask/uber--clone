import pytest
from unittest.mock import patch, MagicMock
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.utils.timezone import now
from datetime import timedelta
import uuid

from apps.payments.models import Payment, LedgerEntry, Payout, WebhookEvent
from apps.payments.services.refund import refund_payment
from apps.payments.services.payout import settle_driver_payout, _platform_user
from apps.rides.models import Ride
from apps.drivers.models import Driver

@pytest.fixture
def platform_user(django_user_model):
    return _platform_user()

@pytest.fixture
def rider(django_user_model):
    uid = uuid.uuid4().hex[:8]
    return django_user_model.objects.create_user(username=f"rider_{uid}", role="rider")

@pytest.fixture
def driver_user(django_user_model):
    uid = uuid.uuid4().hex[:8]
    return django_user_model.objects.create_user(username=f"driver_{uid}", role="driver")

@pytest.fixture
def driver_profile(driver_user):
    profile, _ = Driver.objects.get_or_create(
        user=driver_user, defaults={'status': Driver.Status.ONLINE, 'level': Driver.Level.NORMAL, 'is_verified': True}
    )
    return profile

@pytest.fixture
def ride(rider, driver_profile):
    return Ride.objects.create(
        rider=rider, driver=driver_profile, status=Ride.Status.COMPLETED,
        pickup_lat=12.0, pickup_lng=77.0, drop_lat=12.1, drop_lng=77.1,
        final_fare=Decimal("100.00")
    )

@pytest.fixture
def payment(rider, ride):
    return Payment.objects.create(
        user=rider, ride_id=ride.id, amount=Decimal("100.00"), status=Payment.Status.CAPTURED,
        gateway="razorpay", gateway_payment_id=f"pay_{uuid.uuid4().hex[:8]}"
    )

@pytest.mark.django_db
class TestPaymentsConditionCoverage:

    def test_refund_invalid_status(self, payment):
        payment.status = Payment.Status.CREATED
        payment.save()
        with pytest.raises(ValidationError, match="Payment not refundable"):
            refund_payment(payment=payment, amount=Decimal("10.00"), reason="Test")

    def test_refund_zero_amount(self, payment):
        with pytest.raises(ValidationError, match="Refund amount must be positive"):
            refund_payment(payment=payment, amount=Decimal("0.00"), reason="Test")

    def test_refund_exceeds_amount(self, payment):
        with pytest.raises(ValidationError, match="Refund exceeds refundable amount"):
            refund_payment(payment=payment, amount=Decimal("100.01"), reason="Test")

    @patch('apps.payments.services.refund.razorpay_client')
    def test_refund_gateway_success_partial(self, mock_razorpay, payment, platform_user):
        mock_razorpay.payment.refund.return_value = {"id": "rfnd_test123"}
        
        res = refund_payment(payment=payment, amount=Decimal("50.00"), reason="Partial")
        assert res["refund_id"] == "rfnd_test123"
        
        payment.refresh_from_db()
        assert payment.status == Payment.Status.PARTIALLY_REFUNDED
        assert payment.refunded_amount == Decimal("50.00")

    @patch('apps.payments.services.refund.razorpay_client')
    def test_refund_gateway_success_full(self, mock_razorpay, payment, platform_user):
        mock_razorpay.payment.refund.return_value = {"id": "rfnd_test123"}
        
        res = refund_payment(payment=payment, amount=Decimal("100.00"), reason="Full")
        payment.refresh_from_db()
        assert payment.status == Payment.Status.REFUNDED

    @patch('apps.payments.services.refund.razorpay_client')
    def test_refund_gateway_failure(self, mock_razorpay, payment):
        mock_razorpay.payment.refund.side_effect = Exception("API Down")
        
        with pytest.raises(ValidationError, match="Gateway refund failed"):
            refund_payment(payment=payment, amount=Decimal("50.00"), reason="Fail")

    def test_refund_simulation_without_gateway(self, payment, platform_user):
        payment.gateway = "simulation"
        payment.save()
        
        res = refund_payment(payment=payment, amount=Decimal("50.00"), reason="Sim Partial")
        assert "sim_ref" in res["refund_id"]
        
        payment.refresh_from_db()
        assert payment.status == Payment.Status.PARTIALLY_REFUNDED

    def test_payout_already_processed(self, driver_user):
        payout = Payout.objects.create(
            driver=driver_user, amount=Decimal("100.00"), fee=Decimal("0.00"), net_amount=Decimal("100.00"),
            status=Payout.Status.PAID, reference="ref_1"
        )
        from apps.payments.tasks import execute_driver_payout
        result = execute_driver_payout(payout_id=payout.id)
        assert result is None

    @patch('apps.payments.tasks.create_driver_payout')
    def test_payout_gateway_simulation(self, mock_gw, driver_user):
        payout = Payout.objects.create(
            driver=driver_user, amount=Decimal("100.00"), fee=Decimal("0.00"), net_amount=Decimal("100.00"),
            status=Payout.Status.PROCESSING, reference="ref_simulate"
        )
        mock_gw.return_value = {"id": "pout_sim1", "status": "processed"}
        
        from apps.payments.tasks import execute_driver_payout
        result = execute_driver_payout(payout_id=payout.id)
        assert "initiated" in result
        payout.refresh_from_db()
        assert payout.gateway_payout_id == "pout_sim1"

    @patch('apps.payments.tasks.create_driver_payout')
    def test_payout_gateway_failure(self, mock_gw, driver_user):
        payout = Payout.objects.create(
            driver=driver_user, amount=Decimal("100.00"), fee=Decimal("0.00"), net_amount=Decimal("100.00"),
            status=Payout.Status.PROCESSING, reference="ref_fail"
        )
        mock_gw.side_effect = Exception("Pout Error")
        
        from apps.payments.tasks import execute_driver_payout
        result = execute_driver_payout(payout_id=payout.id)
            
        payout.refresh_from_db()
        assert payout.status == Payout.Status.FAILED
        assert "Pout Error" in result

