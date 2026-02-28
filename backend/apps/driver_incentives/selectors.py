from django.utils import timezone
from .models import DriverIncentive


def get_active_driver_incentives(city):
    now = timezone.now()
    return DriverIncentive.objects.filter(
        is_active=True,
        valid_from__lte=now,
        valid_to__gte=now,
        city=city,
    )
