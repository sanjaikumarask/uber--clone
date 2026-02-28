from apps.offers.models import OfferUsage


def is_user_eligible_for_offer(offer, user):
    if offer.usage_limit_per_user:
        usage_count = OfferUsage.objects.filter(
            offer=offer, user=user
        ).count()
        if usage_count >= offer.usage_limit_per_user:
            return False

    if offer.total_usage_limit:
        if offer.total_usage_count >= offer.total_usage_limit:
            return False

    return True
