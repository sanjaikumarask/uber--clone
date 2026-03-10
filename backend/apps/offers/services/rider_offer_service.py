from django.db import transaction

from apps.offers.models import Offer, OfferUsage
from apps.offers.services.eligibility_service import is_user_eligible_for_offer


def preview_discount(offer, base_fare):
    if offer.discount_type == "FLAT":
        return min(float(offer.value), float(base_fare))

    if offer.discount_type == "PERCENTAGE":
        discount = (float(base_fare) * float(offer.value)) / 100.0
        if offer.max_discount:
            discount = min(discount, float(offer.max_discount))
        return discount

    return 0


@transaction.atomic
def apply_rider_offer(ride):
    if not ride.applied_offer_id:
        return 0

    try:
        offer = Offer.objects.select_for_update().get(id=ride.applied_offer_id)
    except Offer.DoesNotExist:
        return 0

    if not offer.is_valid_now():
        return 0

    if not is_user_eligible_for_offer(offer, ride.rider):
        return 0

    base_fare = float(ride.base_fare)

    if offer.min_ride_value and base_fare < float(offer.min_ride_value):
        return 0

    # Offer model doesn't have min_distance, so we remove that check or assume it's not present.
    # if offer.min_distance and ride.distance < offer.min_distance:
    #     return 0

    discount = preview_discount(offer, base_fare)

    OfferUsage.objects.create(
        offer=offer,
        user=ride.rider,
        ride=ride,
        discount_applied=discount,
    )

    offer.total_usage_count += 1
    offer.save(update_fields=["total_usage_count"])

    return discount
