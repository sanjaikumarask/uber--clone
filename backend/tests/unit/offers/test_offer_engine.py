import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from unittest.mock import MagicMock, patch

from apps.offers.models import Offer, OfferUsage
from apps.offers.services.offer_engine import OfferEngine

@pytest.mark.django_db
class TestOfferEngine:

    @pytest.fixture
    def active_offer(self):
        return Offer.objects.create(
            code="TEST50",
            discount_type="PERCENTAGE",
            value=Decimal("50.00"),
            max_discount=Decimal("200.00"),
            min_ride_value=Decimal("100.00"),
            valid_from=timezone.now() - timedelta(days=1),
            valid_to=timezone.now() + timedelta(days=1),
            is_active=True,
            city="Chennai",
            usage_limit=10,
            per_user_limit=2
        )

    def test_validate_offer_missing_code(self):
        with pytest.raises(ValidationError, match="Offer code is required."):
            OfferEngine.validate_offer(None, MagicMock(), 150)

    def test_validate_offer_invalid_code(self):
        with pytest.raises(ValidationError, match="Invalid or inactive offer code."):
            OfferEngine.validate_offer("INVALID", MagicMock(), 150)

    def test_validate_offer_expired(self, active_offer):
        active_offer.valid_to = timezone.now() - timedelta(minutes=10)
        active_offer.save()
        with pytest.raises(ValidationError, match="This offer has expired."):
            OfferEngine.validate_offer("TEST50", MagicMock(), 150)

    def test_validate_offer_wrong_city(self, active_offer):
        with pytest.raises(ValidationError, match="This offer is not valid in Bangalore."):
            OfferEngine.validate_offer("TEST50", MagicMock(), 150, "Bangalore")

    def test_validate_offer_global_limit_reached(self, active_offer):
        active_offer.usage_limit = 5
        active_offer.total_usage_count = 5
        active_offer.save()
        with pytest.raises(ValidationError, match="This offer has reached its usage limit."):
            OfferEngine.validate_offer("TEST50", MagicMock(), 150)

    def test_validate_offer_min_ride_value(self, active_offer):
        with pytest.raises(ValidationError, match="Minimum ride value of ₹100.00 required"):
            OfferEngine.validate_offer("TEST50", MagicMock(), 50)

    def test_validate_offer_user_limit_reached(self, active_offer, user, ride):
        from apps.offers.models import OfferUsage
        # Create dummy usage with a ride reference to satisfy database constraints
        OfferUsage.objects.create(offer=active_offer, user=user, ride=ride, discount_applied=Decimal("50.00"))
        
        # Create a second usage with another ride
        from apps.rides.models import Ride
        ride2 = Ride.objects.create(
            rider=user,
            pickup_lat=12.9716,
            pickup_lng=77.5946,
            drop_lat=12.9352,
            drop_lng=77.6245,
            status="COMPLETED"
        )
        OfferUsage.objects.create(offer=active_offer, user=user, ride=ride2, discount_applied=Decimal("50.00"))
        
        with pytest.raises(ValidationError, match="You have already used this offer the maximum number of times."):
            OfferEngine.validate_offer("TEST50", user, 150)

    def test_validate_offer_success(self, active_offer, user):
        offer = OfferEngine.validate_offer("TEST50", user, 150, "Chennai")
        assert offer == active_offer

    def test_calculate_discount_percentage(self, active_offer):
        discount = OfferEngine.calculate_discount(active_offer, 300)
        # 50% of 300 is 150, which is below max 200
        assert discount == 150.0

    def test_calculate_discount_percentage_capped(self, active_offer):
        discount = OfferEngine.calculate_discount(active_offer, 500)
        # 50% of 500 is 250, but max is 200
        assert discount == 200.0

    def test_calculate_discount_flat(self, active_offer):
        active_offer.discount_type = "FLAT"
        active_offer.value = Decimal("75.00")
        active_offer.max_discount = None
        active_offer.save()

        discount = OfferEngine.calculate_discount(active_offer, 300)
        assert discount == 75.0
        
        # Flat discount shouldn't exceed ride value
        discount2 = OfferEngine.calculate_discount(active_offer, 50)
        assert discount2 == 50.0

    def test_apply_offer(self, active_offer, ride):
        ride.base_fare = Decimal("200.00")
        ride.city = "Chennai"
        
        discount = OfferEngine.apply_offer(ride, "TEST50")
        
        assert discount == 100.0
        ride.refresh_from_db()
        assert ride.applied_offer == active_offer
        assert ride.discount_amount == Decimal("100.00")

    def test_finalize_usage(self, active_offer, ride):
        ride.applied_offer = active_offer
        ride.discount_amount = Decimal("50.00")
        ride.save()
        
        initial_usage = active_offer.total_usage_count
        
        OfferEngine.finalize_usage(ride)
        
        # Verify usage record created and counter incremented
        assert OfferUsage.objects.filter(offer=active_offer, ride=ride).exists()
        active_offer.refresh_from_db()
        assert active_offer.total_usage_count == initial_usage + 1
        
        # Idempotency check
        OfferEngine.finalize_usage(ride)
        active_offer.refresh_from_db()
        assert active_offer.total_usage_count == initial_usage + 1 # Still +1
