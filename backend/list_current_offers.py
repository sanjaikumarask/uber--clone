import os
import django
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.offers.models import Offer

offers = Offer.objects.all().order_by('-created_at')

print("-" * 65)
print(f"{'CODE':<15} | {'TITLE':<20} | {'DISCOUNT':<10} | {'STATUS'}")
print("-" * 65)

if not offers.exists():
    print("No offers found in the database.")
else:
    for o in offers:
        discount = f"{o.value}%" if o.discount_type == 'PERCENTAGE' else f"INR {o.value}"
        now = timezone.now()
        is_valid = o.is_active and o.valid_from <= now <= o.valid_to
        status = "✅ Active" if is_valid else "❌ Inactive/Expired"
        print(f"{o.code:<15} | {o.title[:20]:<20} | {discount:<10} | {status}")

print("-" * 65)
print(f"Total Offers: {offers.count()}")
