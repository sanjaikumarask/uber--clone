import pytest
from decimal import Decimal
from django.utils import timezone
from apps.users.models import User
from apps.drivers.models import Driver
from apps.rides.models import Ride
from apps.payments.models import LedgerEntry, Payment
from apps.payments.services.payout import settle_driver_payout
from apps.drivers.services.trust import register_completed_ride

@pytest.mark.django_db
def test_driver_lifecycle_earnings(client):
    """
    Scenario:
    1. Driver Setup & Online
    2. Ride Assigned & Completed
    3. Metrics Updated
    4. Payout Calculated & Credited
    """
    # 1. Driver Setup
    driver_user = User.objects.create_user(
        username="driver_life", 
        password="password", 
        role="driver", 
        phone="+1234567890",
    )
    # Ensure platform user exists
    User.objects.create_user(pk=1, username="plaform_admin", password="p", role="admin", phone="+0000000000")

    driver = driver_user.driver
    driver.status = Driver.Status.ONLINE
    driver.save()
    
    # 2. Ride Flow
    rider_user = User.objects.create_user(
        username="rider_life", 
        password="password", 
        role="rider", 
        phone="+0987654321"
    )
    
    ride = Ride.objects.create(
        rider=rider_user,
        driver=driver,
        pickup_lat=10.0, pickup_lng=10.0,
        drop_lat=10.1, drop_lng=10.1,
        status=Ride.Status.ASSIGNED
    )
    
    # Simulate Ride Completion
    ride.status = Ride.Status.COMPLETED
    ride.save()
    
    # 3. Trust Logic Trigger
    # Simulate API calling service
    register_completed_ride(driver)
    
    driver.refresh_from_db()
    # Check stats updated
    # DriverStats created automatically? `get_or_create` used in logic.
    assert driver.stats.completed_rides == 1
    
    # 4. Payment & Earnings
    payment = Payment.objects.create(
        user=rider_user,
        ride_id=ride.id,
        amount=Decimal("100.00"),
        status=Payment.Status.CAPTURED
    )
    
    # Process Payout
    settle_driver_payout(ride=ride, payment=payment)
    
    # 5. Verify Ledger
    # Driver should get 80% (assuming 20% commission)
    driver_entry = LedgerEntry.objects.filter(
        user=driver_user,
        ride_id=ride.id,
        entry_type=LedgerEntry.Type.CREDIT,
        reason=LedgerEntry.Reason.DRIVER_EARNING 
    ).first()
    
    assert driver_entry is not None
    assert driver_entry.amount == Decimal("80.00")
    
    # Platform commision
    platform_entry = LedgerEntry.objects.filter(
        reference__startswith="commission:",
        ride_id=ride.id
    ).first()
    assert platform_entry.amount == Decimal("20.00")
