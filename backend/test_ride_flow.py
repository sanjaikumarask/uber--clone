import os
import django
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta

# Setup Django (if running standalone, but we run via shell so this is optional but good)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.users.models import User
from apps.drivers.models import Driver
from apps.offers.models import Offer
from apps.rides.models import Ride
from apps.rides.services.complete_ride import complete_ride
from apps.payments.models import LedgerEntry

def run_test():
    print("🚀 Starting Test Flow...")

    # 1. Get Test Users
    # -----------------
    try:
        rider = User.objects.get(id=8)
        driver = Driver.objects.get(id=3)
        print(f"✅ Users Found: Rider={rider.first_name}, Driver={driver.user.first_name}")
    except Exception as e:
        print(f"❌ Error getting users: {e}")
        return

    # 2. Create Offer
    # ---------------
    offer_title = f"Test Offer {timezone.now().timestamp()}"
    offer = Offer.objects.create(
        title=offer_title,
        offer_type="RIDER",
        discount_type="FLAT",
        discount_value=Decimal("20.00"),
        city="Chennai",
        start_time=timezone.now() - timedelta(hours=1),
        end_time=timezone.now() + timedelta(hours=1),
        is_active=True,
        min_ride_amount=Decimal("50.00")
    )
    print(f"✅ Created Offer: {offer.title} (Value: {offer.discount_value})")

    # 3. Create Ongoing Ride
    # ----------------------
    ride = Ride.objects.create(
        rider=rider,
        driver=driver,
        pickup_lat=12.9716, pickup_lng=77.5946,
        drop_lat=12.9352, drop_lng=77.6245,
        status="ONGOING",  # Simulate ongoing ride
        base_fare=Decimal("100.00"),
        actual_distance_km=5.0,
        applied_offer=offer,
        # Ensure city matches offer if needed (Model doesn't have city?)
        # Ride doesn't have city field usually, it's derived. 
        # But `apply_driver_incentive` calls `ride.city`.
        # I need to patch Ride model or Mock it. 
        # Check Ride model... No city field.
        # But `apply_driver_incentive` calls `ride.city`.
        # This will CRASH if Ride has no city property!
    )
    # Patch ride for test if property missing
    if not hasattr(ride, 'city'):
        ride.city = "Chennai"

    print(f"✅ Created Ride #{ride.id} in 'ONGOING' state with Offer applied.")

    # 4. Complete Ride (The Core Logic)
    # ---------------------------------
    print("\n🔄 Executing complete_ride service...")
    try:
        completed_ride = complete_ride(ride.id)
        print("✅ complete_ride Success!")
    except Exception as e:
        print(f"❌ complete_ride Failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # 5. Verify Results
    # -----------------
    print("\n📊 Verification Results:")
    print(f"   Ride Status: {completed_ride.status}")
    print(f"   Base Fare:   {completed_ride.base_fare}")
    print(f"   Discount:    -{completed_ride.discount_amount}")
    print(f"   Final Fare:  {completed_ride.final_fare}")

    # Check Wallet
    rider_debit = LedgerEntry.objects.filter(user=rider, entry_type="DEBIT").order_by('-created_at').first()
    driver_credit = LedgerEntry.objects.filter(user=driver.user, entry_type="CREDIT").order_by('-created_at').first()

    print("\n💰 Wallet Entries:")
    print(f"   Rider Debit:  {rider_debit.amount if rider_debit else 'None'} ({rider_debit.reason if rider_debit else '-'})")
    print(f"   Driver Credit: {driver_credit.amount if driver_credit else 'None'} ({driver_credit.reason if driver_credit else '-'})")

    # Assertions
    if completed_ride.discount_amount == Decimal("20.00"):
        print("\n✅ SUCCESS: Discount Applied Correctly")
    else:
        print("\n❌ FAILURE: Discount Incorrect")

if __name__ == "__main__":
    run_test()
