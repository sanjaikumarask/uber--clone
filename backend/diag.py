import os
import django
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.payments.models import Payment, LedgerEntry
from django.db.models import Sum

print("--- FULL AUDIT START ---")

captured_payments = Payment.objects.filter(status='CAPTURED')
total_captured = captured_payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

all_driver_credits = LedgerEntry.objects.filter(
    entry_type=LedgerEntry.Type.CREDIT,
    reason=LedgerEntry.Reason.DRIVER_EARNING
).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

platform_comms = LedgerEntry.objects.filter(
    entry_type=LedgerEntry.Type.CREDIT, 
    reason=LedgerEntry.Reason.PLATFORM_COMMISSION
).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

total_credits = all_driver_credits + platform_comms
print(f"Total Captured Payments: {total_captured} ({captured_payments.count()} records)")
print(f"Total Credits (Global): {total_credits}")
print(f"Global Drift: {total_captured - total_credits}")

print("\n--- ANALYZING UNSETTLED PAYMENTS ---")
unsettled_payments = []
for p in captured_payments:
    ride_credits = LedgerEntry.objects.filter(
        ride_id=p.ride_id, 
        entry_type=LedgerEntry.Type.CREDIT, 
        reason__in=[LedgerEntry.Reason.DRIVER_EARNING, LedgerEntry.Reason.PLATFORM_COMMISSION]
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    if ride_credits != p.amount:
        print(f"Unsettled Payment: ID={p.id}, RideID={p.ride_id}, Amount={p.amount}, Credits={ride_credits}, Diff={p.amount - ride_credits}")

print("--- FULL AUDIT END ---")
