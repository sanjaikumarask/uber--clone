from django.db import transaction
from apps.offers.models import OfferUsage, Offer
from apps.offers.services.eligibility_service import is_user_eligible_for_offer


def preview_discount(offer, base_fare):
    if offer.discount_type == "FLAT":
        return min(offer.discount_value, base_fare)

    if offer.discount_type == "PERCENTAGE":
        discount = (base_fare * offer.discount_value) / 100
        if offer.max_discount_cap:
            discount = min(discount, offer.max_discount_cap)
        return discount

    return 0


@transaction.atomic
def apply_rider_offer(ride):
    if not ride.applied_offer_id:
        return 0

    offer = Offer.objects.select_for_update().get(id=ride.applied_offer_id)

    if not offer.is_valid_now():
        return 0

    if not is_user_eligible_for_offer(offer, ride.rider):
        return 0

    base_fare = ride.base_fare

    if offer.min_ride_amount and base_fare < offer.min_ride_amount:
        return 0

    if offer.min_distance and ride.distance < offer.min_distance:
        return 0

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
