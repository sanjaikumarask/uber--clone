import os
import django
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.payments.models import Payment, LedgerEntry

captured_payments = Payment.objects.filter(status='CAPTURED')
print("Captured payments without earning entries:")
for p in captured_payments:
    earning_exists = LedgerEntry.objects.filter(
        reference=f"earning:{p.ride_id}",
        reason=LedgerEntry.Reason.DRIVER_EARNING
    ).exists()
    
    if not earning_exists:
        print(f"NO EARNING FOR Payment ID {p.id}, Ride {p.ride_id}")
