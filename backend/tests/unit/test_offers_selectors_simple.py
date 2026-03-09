import pytest
from datetime import timedelta
from django.utils import timezone
from apps.offers.models import Offer
from apps.offers.selectors import get_active_rider_offers

@pytest.mark.django_db
def test_get_active_rider_offers_simple():
    now = timezone.now()
    Offer.objects.create(
        title="Global Promo", code="GLOBAL", is_active=True,
        discount_type="FLAT", value=10,
        valid_from=now - timedelta(days=1), valid_to=now + timedelta(days=1)
    )
    Offer.objects.create(
        title="City Promo", code="CITY", is_active=True, city="Chennai",
        discount_type="PERCENTAGE", value=15,
        valid_from=now - timedelta(days=1), valid_to=now + timedelta(days=1)
    )
    
    assert get_active_rider_offers().count() == 2
    assert get_active_rider_offers(city="Chennai").count() == 2
    assert get_active_rider_offers(city="Delhi").count() == 1
