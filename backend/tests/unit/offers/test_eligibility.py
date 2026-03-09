import pytest
from apps.offers.models import Offer, OfferUsage
from apps.offers.services.eligibility_service import is_user_eligible_for_offer
from apps.users.models import User
from apps.rides.models import Ride

@pytest.mark.django_db
def test_is_user_eligible_for_offer():
    user = User.objects.create_user(username="u_elig", phone="+917770001111")
    offer = Offer.objects.create(
        code="ELIGIBLE",
        discount_type="FLAT",
        value=50,
        per_user_limit=1,
        usage_limit=5,
        valid_from="2020-01-01",
        valid_to="2099-01-01"
    )
    
    # 1. Eligible initially
    assert is_user_eligible_for_offer(offer, user) is True
    
    # 2. Used once -> Not eligible (per_user_limit=1)
    ride = Ride.objects.create(
        rider=user,
        pickup_lat=12.0, pickup_lng=77.0,
        drop_lat=12.1, drop_lng=77.1,
        base_fare=100
    )
    OfferUsage.objects.create(offer=offer, user=user, ride=ride, discount_applied=50)
    assert is_user_eligible_for_offer(offer, user) is False
    
    # 3. Total usage limit
    offer2 = Offer.objects.create(
        code="TOTAL_LIMIT",
        discount_type="FLAT",
        value=50,
        usage_limit=1,
        valid_from="2020-01-01",
        valid_to="2099-01-01"
    )
    offer2.total_usage_count = 1
    offer2.save()
    assert is_user_eligible_for_offer(offer2, user) is False
