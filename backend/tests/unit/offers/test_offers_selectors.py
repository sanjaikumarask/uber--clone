import pytest
from django.utils import timezone
import datetime
from apps.offers.models import Offer
from apps.offers.selectors import get_active_rider_offers

@pytest.mark.django_db
class TestOfferSelectors:
    def test_get_active_rider_offers_no_city(self):
        now = timezone.now()
        # Active offer
        offer1 = Offer.objects.create(
            code="ACTIVE1", title="Active", discount_type="PERCENTAGE", value=10, 
            is_active=True, valid_from=now - datetime.timedelta(days=1), valid_to=now + datetime.timedelta(days=1)
        )
        # Inactive offer
        Offer.objects.create(
            code="INACTIVE1", title="Inactive", discount_type="PERCENTAGE", value=10, 
            is_active=False, valid_from=now - datetime.timedelta(days=1), valid_to=now + datetime.timedelta(days=1)
        )
        
        qs = get_active_rider_offers()
        assert qs.count() == 1
        assert offer1 in qs

    def test_get_active_rider_offers_with_city(self):
        now = timezone.now()
        Offer.objects.create(
            code="NYC1", title="NYC", discount_type="PERCENTAGE", value=10, 
            is_active=True, valid_from=now - datetime.timedelta(days=1), valid_to=now + datetime.timedelta(days=1),
            city="NYC"
        )
        Offer.objects.create(
            code="GLOBAL1", title="Global", discount_type="PERCENTAGE", value=10, 
            is_active=True, valid_from=now - datetime.timedelta(days=1), valid_to=now + datetime.timedelta(days=1),
            city=""
        )
        
        qs_nyc = get_active_rider_offers(city="NYC")
        assert qs_nyc.count() == 2
        
        qs_sfo = get_active_rider_offers(city="SFO")
        assert qs_sfo.count() == 1  # Only the global one
        assert qs_sfo.first().code == "GLOBAL1"
        
    def test_get_active_rider_offers_none(self):
        qs = get_active_rider_offers(city=None)
        assert qs.count() == 0
