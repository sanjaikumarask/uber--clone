import os

import django

# Setup Django standalone
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.payments.models import LedgerEntry, Payment
from apps.payments.services.payout import settle_driver_payout
from apps.rides.models import Ride


def fix_drift():
    captured_payments = Payment.objects.filter(status="CAPTURED")
    fixed_count = 0

    for p in captured_payments:
        # Check if true earning exists
        if not LedgerEntry.objects.filter(reference=f"earning:{p.ride_id}").exists():
            try:
                ride = Ride.objects.get(id=p.ride_id)
                print(
                    f"Fixing payout for Ride {p.ride_id}, Payment {p.id}, Amount {p.amount}"
                )
                settle_driver_payout(ride=ride, payment=p)
                fixed_count += 1
            except Exception as e:
                print(f"Failed to fix Ride {p.ride_id}: {e}")

    print(f"Fixed {fixed_count} missing payouts.")


if __name__ == "__main__":
    fix_drift()
