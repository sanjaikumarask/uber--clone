import pytest
from django.utils import timezone
import datetime
from apps.driver_incentives.models import DriverIncentive
from apps.driver_incentives.selectors import get_active_driver_incentives

@pytest.mark.django_db
class TestDriverIncentiveSelectors:
    def test_get_active_driver_incentives_success(self):
        now = timezone.now()
        incentive1 = DriverIncentive.objects.create(
            title="Bonus NYC", type=DriverIncentive.Type.ZONE, 
            reward_amount=50,
            is_active=True, valid_from=now - datetime.timedelta(days=1), valid_to=now + datetime.timedelta(days=1),
            city="NYC"
        )
        DriverIncentive.objects.create(
            title="Bonus SFO", type=DriverIncentive.Type.ZONE, 
            reward_amount=50,
            is_active=True, valid_from=now - datetime.timedelta(days=1), valid_to=now + datetime.timedelta(days=1),
            city="SFO"
        )
        DriverIncentive.objects.create(
            title="Inactive NYC", type=DriverIncentive.Type.ZONE, 
            reward_amount=50,
            is_active=False, valid_from=now - datetime.timedelta(days=1), valid_to=now + datetime.timedelta(days=1),
            city="NYC"
        )
        
        qs = get_active_driver_incentives("NYC")
        assert qs.count() == 1
        assert incentive1 in qs

    def test_get_active_driver_incentives_no_matches(self):
        qs = get_active_driver_incentives("LONDON")
        assert qs.count() == 0

    def test_get_active_driver_incentives_invalid(self):
        qs = get_active_driver_incentives(None)
        assert qs.count() == 0
