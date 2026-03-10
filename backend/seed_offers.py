import os
from datetime import timedelta

import django
from django.utils import timezone

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.offers.models import Offer

# Sample Offers
offers_data = [
    {
        "code": "WELCOME50",
        "title": "Welcome Discount",
        "description": "Get ₹50 off on your first ride!",
        "discount_type": "FLAT",
        "value": 50.00,
        "valid_from": timezone.now(),
        "valid_to": timezone.now() + timedelta(days=30),
        "is_active": True,
        "city": "Chennai",
    },
    {
        "code": "PEAK20",
        "title": "Peak Hour Special",
        "description": "20% off during peak hours!",
        "discount_type": "PERCENTAGE",
        "value": 20.00,
        "valid_from": timezone.now(),
        "valid_to": timezone.now() + timedelta(days=7),
        "is_active": True,
        "city": "Chennai",
    },
    {
        "code": "SUMMER10",
        "title": "Summer Sale",
        "description": "Flat ₹10 off on all rides.",
        "discount_type": "FLAT",
        "value": 10.00,
        "valid_from": timezone.now(),
        "valid_to": timezone.now() + timedelta(days=60),
        "is_active": False,
        "city": "Chennai",
    },
]

for data in offers_data:
    Offer.objects.get_or_create(code=data["code"], defaults=data)

print(f"Successfully seeded {len(offers_data)} sample offers.")
