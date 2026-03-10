from apps.offers.models import OfferUsage


def is_user_eligible_for_offer(offer, user):
    if offer.per_user_limit:
        usage_count = OfferUsage.objects.filter(offer=offer, user=user).count()
        if usage_count >= offer.per_user_limit:
            return False

    if offer.usage_limit and offer.total_usage_count >= offer.usage_limit:
        return False

    return True
