import pytest
from apps.offers.services.eligibility_service import is_user_eligible_for_offer
from apps.offers.models import Offer, OfferUsage
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

User = get_user_model()

@pytest.mark.django_db
def test_is_user_eligible_for_offer():
    user = User.objects.create(username="elig_user", phone="1112223334")
    now = timezone.now()
    offer = Offer.objects.create(
        code="LIMIT1", title="Limit 1", discount_type="FLAT", value=5,
        per_user_limit=1, valid_from=now-timedelta(1), valid_to=now+timedelta(1)
    )
    
    # Eligible initially
    assert is_user_eligible_for_offer(offer, user) is True
    
    # Create fake usage (we need a ride, or we can mock/fake models if needed, 
    # but OfferUsage just needs offer and user fields to count)
    # Actually OfferUsage has a ForeignKey to Ride. 
    # Let's mock the count or create a minimal ride.
    from apps.rides.models import Ride
    ride = Ride.objects.create(
        rider=user, pickup_lat=0, pickup_lng=0, drop_lat=0, drop_lng=0
    )
    OfferUsage.objects.create(offer=offer, user=user, ride=ride, discount_applied=5)
    
    # Not eligible anymore
    assert is_user_eligible_for_offer(offer, user) is False
