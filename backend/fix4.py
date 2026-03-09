import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.payments.models import LedgerEntry

entries = LedgerEntry.objects.filter(reason=LedgerEntry.Reason.DRIVER_EARNING)
fixed = 0

for e in entries:
    if not e.reference.startswith("earning:"):
        print(f"Fixing LEDGER ENTRY ID={e.id}, ref={e.reference}, current={e.reason}")
        e.reason = LedgerEntry.Reason.INCENTIVE
        e.save(update_fields=["reason"])
        fixed += 1

print(f"Fixed {fixed} ledger entries.")
