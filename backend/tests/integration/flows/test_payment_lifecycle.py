import pytest
from decimal import Decimal
from unittest.mock import patch
from apps.users.models import User
from apps.drivers.models import Driver
from apps.rides.models import Ride
from apps.payments.models import LedgerEntry, Payment
from apps.payments.services.payout import settle_driver_payout
from apps.payments.services.refund import refund_payment

@pytest.mark.django_db
@patch("apps.payments.services.refund.razorpay_client")
def test_payment_lifecycle_refund(mock_rp, client):
    """
    Scenario:
    1. Ride Payment Captured
    2. Payout Settled
    3. Refund Initiated (Partial)
    4. Wallet Adjusted
    """
    # Setup
    driver_user = User.objects.create_user(username="driver_pay", password="p", role="driver", phone="+1112223333")
    driver = driver_user.driver
    
    rider_user = User.objects.create_user(username="rider_pay", password="p", role="rider", phone="+4445556666")
    
    # Ride
    ride = Ride.objects.create(
        rider=rider_user, 
        driver=driver, 
        pickup_lat=0, pickup_lng=0, drop_lat=0, drop_lng=0, 
        status=Ride.Status.COMPLETED
    )
    
    # Create Platform User (Admin)
    admin_user = User.objects.create_user(pk=1, username="admin_pay", password="p", role="admin", phone="+0000000000")

    # 1. Capture Payment
    payment = Payment.objects.create(
        user=rider_user, 
        ride_id=ride.id,
        amount=Decimal("200.00"),
        status=Payment.Status.CAPTURED,
        gateway_payment_id="pay_12345"
    )
    
    # 2. Settle Driver (Gets 160.00)
    settle_driver_payout(ride=ride, payment=payment)
    assert LedgerEntry.objects.filter(user=driver_user, entry_type="CREDIT").first().amount == Decimal("160.00")
    
    # 3. Simulate Refund (Mock Razorpay Success)
    mock_rp.payment.refund.return_value = {"id": "ref_999", "status": "processed"}
    
    # Partial Refund: 50.00
    res = refund_payment(
        payment=payment,
        amount=Decimal("50.00"),
        reason="bad_experience",
        initiated_by=admin_user
    )
    
    assert res["status"] == "PARTIALLY_REFUNDED"
    
    # 4. Check Rider Ledger (Credit 50.00)
    rider_refund = LedgerEntry.objects.filter(
        user=rider_user, 
        ride_id=ride.id,
        entry_type="CREDIT",
        reason="bad_experience"
    ).first()
    
    assert rider_refund.amount == Decimal("50.00")
    
    # Verify Payment updated
    payment.refresh_from_db()
    assert payment.refunded_amount == Decimal("50.00")
    assert payment.status == "PARTIALLY_REFUNDED"
    
    # Gateway called
    mock_rp.payment.refund.assert_called_once()
