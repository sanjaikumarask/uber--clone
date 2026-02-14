import pytest
from unittest.mock import patch
from decimal import Decimal
from apps.users.models import User
from apps.drivers.models import Driver
from apps.rides.models import Ride
from apps.payments.models import LedgerEntry, Payment
from apps.supports.models import SupportTicket
from apps.supports.services import open_support_ticket, resolve_with_refund

@pytest.mark.django_db
@patch("apps.payments.services.refund.razorpay_client")
def test_support_refund_flow(mock_rp, client):
    """
    Scenario:
    1. User Raises Ticket
    2. Admin Resolves Ticket via Refund
    3. Refund Processed & Ticket Closed
    """
    # Setup
    rider = User.objects.create_user(username="rider_sup", phone="+111222")
    # Driver needs to be linked to ride for ticket validation logic?
    # Logic in services.py: `if ride.rider != user and (not ride.driver or ride.driver.user != user): raise ValidationError`
    # So rider check is sufficient.
    
    driver_user = User.objects.create_user(username="driver_sup", phone="+222333")
    driver = Driver.objects.create(user=driver_user)
    
    ride = Ride.objects.create(
        rider=rider, 
        driver=driver, 
        pickup_lat=10.0, pickup_lng=10.0,
        drop_lat=10.1, drop_lng=10.1,
        status=Ride.Status.COMPLETED
    )
    
    # Payment Setup
    payment = Payment.objects.create(
        user=rider, 
        ride_id=ride.id, 
        amount=Decimal("100"), 
        status=Payment.Status.CAPTURED, 
        gateway_payment_id="p123"
    )
    
    # 1. User Raises Ticket
    ticket = open_support_ticket(
        ride=ride, 
        user=rider, 
        reason="rude_driver", 
        description="very rude"
    )
    assert ticket.status == SupportTicket.Status.OPEN
    
    # 2. Admin Resolves
    admin = User.objects.create_user(username="admin_sup", role="admin", phone="+000111")
    
    # Mock refund OK
    mock_rp.payment.refund.return_value = {"id": "ref_999", "status": "processed"}
    
    resolve_with_refund(
        ticket=ticket,
        admin=admin,
        refund_amount=Decimal("10.00"),
        reason_note="Apology refund"
    )
    
    # 3. Check States
    ticket.refresh_from_db()
    assert ticket.status == SupportTicket.Status.RESOLVED
    assert ticket.resolution_note == "Apology refund"
    
    # Check Refund Logic
    payment.refresh_from_db()
    assert payment.refunded_amount == Decimal("10.00")
    
    # Check Ledger Logic (Refund Credit)
    refund_credit = LedgerEntry.objects.filter(
        user=rider,
        ride_id=ride.id,
        entry_type="CREDIT", # Refund is credit to user
        reference__startswith="refund:"
    ).first()
    
    assert refund_credit is not None
    assert refund_credit.amount == Decimal("10.00")
