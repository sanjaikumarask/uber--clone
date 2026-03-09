import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.payments.models import LedgerEntry, Payment
from apps.payments.services.payout import settle_driver_payout
from apps.rides.models import Ride

captured_payments = Payment.objects.filter(status="CAPTURED")
fixed_count = 0

for p in captured_payments:
    ride = Ride.objects.get(id=p.ride_id)
    # Check if a DRIVER_EARNING ledger entry exists for this ride that has reference starting with earning:
    earning_exists = LedgerEntry.objects.filter(
        reference=f"earning:{p.ride_id}", reason=LedgerEntry.Reason.DRIVER_EARNING
    ).exists()

    if not earning_exists:
        try:
            print(f"Fixing payout for Ride {p.ride_id}, Amount {p.amount}")
            settle_driver_payout(ride=ride, payment=p)
            fixed_count += 1
        except Exception as e:
            print(f"Failed to settle ride {p.ride_id}: {e}")

print(f"Fixed {fixed_count} missing pay cycles.")
