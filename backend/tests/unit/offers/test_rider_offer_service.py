import pytest
from apps.offers.models import Offer, OfferUsage
from apps.offers.services.rider_offer_service import apply_rider_offer, preview_discount
from apps.users.models import User
from apps.rides.models import Ride

@pytest.mark.django_db
def test_preview_discount():
    offer = Offer(discount_type="PERCENTAGE", value=20, max_discount=50)
    assert preview_discount(offer, 100) == 20
    assert preview_discount(offer, 500) == 50 # capped at 50
    
    offer_flat = Offer(discount_type="FLAT", value=30)
    assert preview_discount(offer_flat, 100) == 30
    assert preview_discount(offer_flat, 20) == 20 # capped at base_fare

@pytest.mark.django_db
def test_apply_rider_offer():
    user = User.objects.create_user(username="u_apply", phone="+917770002222")
    offer = Offer.objects.create(
        code="APPLY",
        discount_type="PERCENTAGE",
        value=10,
        valid_from="2020-01-01",
        valid_to="2099-01-01",
        min_ride_value=50,
        per_user_limit=2
    )
    
    ride = Ride.objects.create(
        rider=user,
        pickup_lat=12.0, pickup_lng=77.0,
        drop_lat=12.1, drop_lng=77.1,
        base_fare=100,
        applied_offer=offer
    )
    
    # 1. Successful apply
    discount = apply_rider_offer(ride)
    assert discount == 10
    assert OfferUsage.objects.filter(offer=offer, ride=ride, user=user).exists()
    offer.refresh_from_db()
    assert offer.total_usage_count == 1

    
    # 2. Min ride value failure
    ride2 = Ride.objects.create(
        rider=user,
        pickup_lat=12.0, pickup_lng=77.0,
        drop_lat=12.1, drop_lng=77.1,
        base_fare=40, # below 50
        applied_offer=offer
    )
    discount2 = apply_rider_offer(ride2)
    assert discount2 == 0
    
    # 3. Expiry failure
    offer.valid_to = "2020-01-02"
    offer.save()
    ride3 = Ride.objects.create(
        rider=user,
        pickup_lat=12.0, pickup_lng=77.0,
        drop_lat=12.1, drop_lng=77.1,
        base_fare=100,
        applied_offer=offer
    )
    discount3 = apply_rider_offer(ride3)
    assert discount3 == 0
