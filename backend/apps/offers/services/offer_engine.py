from django.core.exceptions import ValidationError
from django.db import transaction

from apps.offers.models import Offer, OfferUsage


class OfferEngine:

    @staticmethod
    def validate_offer(code, user, ride_value, city=None):
        """
        Validates an offer code against all business rules.
        Raises ValidationError with a clear message if invalid.
        Returns the Offer object if valid.
        """
        if not code:
            raise ValidationError("Offer code is required.")

        try:
            offer = Offer.objects.get(code=code, is_active=True)
        except Offer.DoesNotExist:
            raise ValidationError("Invalid or inactive offer code.")

        # Expiry check
        if not offer.is_valid_now():
            raise ValidationError("This offer has expired.")

        # City check (only if offer has a city restriction)
        if offer.city and city and offer.city.strip() != city.strip():
            raise ValidationError(f"This offer is not valid in {city}.")

        # Global usage limit
        if (
            offer.usage_limit is not None
            and offer.total_usage_count >= offer.usage_limit
        ):
            raise ValidationError("This offer has reached its usage limit.")

        # Minimum ride value
        if float(ride_value) < float(offer.min_ride_value):
            raise ValidationError(
                f"Minimum ride value of ₹{offer.min_ride_value} required for this offer."
            )

        # Per-user limit
        user_usage_count = OfferUsage.objects.filter(offer=offer, user=user).count()
        if user_usage_count >= offer.per_user_limit:
            raise ValidationError(
                "You have already used this offer the maximum number of times."
            )

        return offer

    @staticmethod
    def calculate_discount(offer, ride_value):
        """
        Returns the discount amount (capped at ride_value and max_discount).
        """
        ride_value = float(ride_value)

        if offer.discount_type == "FLAT":
            discount = float(offer.value)
        else:  # PERCENTAGE
            discount = (ride_value * float(offer.value)) / 100.0

        # Cap at max_discount
        if offer.max_discount:
            discount = min(discount, float(offer.max_discount))

        # Never exceed ride value
        return min(discount, ride_value)

    @staticmethod
    @transaction.atomic
    def apply_offer(ride, code):
        """
        Validates and applies an offer to a ride (pre-completion stage).
        Records the applied offer on the ride object.
        Actual usage is only finalized after ride completion.
        """
        offer = OfferEngine.validate_offer(
            code, ride.rider, ride.base_fare, getattr(ride, "city", None)
        )
        discount = OfferEngine.calculate_discount(offer, ride.base_fare)

        ride.applied_offer = offer
        ride.discount_amount = discount
        ride.save(update_fields=["applied_offer", "discount_amount"])

        return discount

    @staticmethod
    @transaction.atomic
    def finalize_usage(ride):
        """
        Called after ride completion.
        Records actual usage and increments the global usage counter atomically.
        Idempotent: skips if already finalized (OfferUsage record exists for this ride).
        """
        if not ride.applied_offer_id:
            return

        # Idempotency guard: don't double-credit
        if OfferUsage.objects.filter(
            offer_id=ride.applied_offer_id, ride=ride
        ).exists():
            return

        offer = Offer.objects.select_for_update().get(id=ride.applied_offer_id)

        OfferUsage.objects.create(
            offer=offer,
            user=ride.rider,
            ride=ride,
            discount_applied=ride.discount_amount,
        )

        offer.total_usage_count += 1
        offer.save(update_fields=["total_usage_count"])
