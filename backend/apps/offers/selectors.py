from django.utils import timezone
from .models import Offer


def get_active_rider_offers(city=None):
    now = timezone.now()
    qs = Offer.objects.filter(
        is_active=True,
        valid_from__lte=now,
        valid_to__gte=now,
    )
    # Filter by city only if city is provided (city=None shows all offers globally)
    if city:
        qs = qs.filter(city__in=[city, None, ""])
    return qs
