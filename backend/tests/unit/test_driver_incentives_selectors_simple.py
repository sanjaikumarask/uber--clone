import pytest
from datetime import timedelta
from django.utils import timezone
from apps.driver_incentives.models import DriverIncentive
from apps.driver_incentives.selectors import get_active_driver_incentives

@pytest.mark.django_db
def test_get_active_driver_incentives_simple():
    now = timezone.now()
    DriverIncentive.objects.create(
        title="Chennai Bonus", city="Chennai", is_active=True,
        reward_amount=500,
        valid_from=now - timedelta(days=1), valid_to=now + timedelta(days=1)
    )
    
    assert get_active_driver_incentives("Chennai").count() == 1
    assert get_active_driver_incentives("Delhi").count() == 0
