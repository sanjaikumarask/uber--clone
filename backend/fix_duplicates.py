import os
import sys

# Setup django environment
sys.path.append("/home/sanjai/dev/uber-backend/backend")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

import uuid

from django.db.models import Count

from apps.payments.models import LedgerEntry

# Find duplicate references
duplicates = (
    LedgerEntry.objects.values("reference")
    .annotate(Count("id"))
    .filter(id__count__gt=1)
    .exclude(reference__isnull=True)
)

for dup in duplicates:
    ref = dup["reference"]
    entries = LedgerEntry.objects.filter(reference=ref).order_by("id")
    # Keep the first one, modify the rest
    for i, entry in enumerate(entries[1:], start=1):
        # We append a short UUID just to guarantee uniqueness
        entry.reference = f"{ref}_{uuid.uuid4().hex[:8]}"
        entry.save(update_fields=["reference"])
        print(f"Fixed duplicate reference {ref} to {entry.reference}")

print("Deduplication complete.")
