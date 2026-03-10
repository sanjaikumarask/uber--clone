import pytest
from rest_framework.test import APIClient

from apps.drivers.models import Driver
from apps.users.models import User


@pytest.mark.django_db
class TestDriverFlow:
    def setup_method(self):
        self.client = APIClient()

        self.user = User.objects.create_user(
            username="driver1",
            password="pass1234",
            role=User.ROLE_DRIVER,
        )

        # Explicitly create driver profile (no auto-signal)
        Driver.objects.get_or_create(
            user=self.user, defaults={"status": Driver.Status.OFFLINE}
        )
        self.driver = Driver.objects.get(user=self.user)

        self.client.force_authenticate(user=self.user)

    def test_driver_go_online_and_update_location(self):
        res = self.client.post("/api/drivers/online/")
        assert res.status_code == 200

        self.driver.refresh_from_db()
        assert self.driver.status == Driver.Status.ONLINE

        res = self.client.post(
            "/api/drivers/location/",
            {"lat": 12.9716, "lng": 77.5946},
            format="json",
        )
        assert res.status_code == 200

        self.driver.refresh_from_db()
        assert self.driver.last_lat == 12.9716
        assert self.driver.last_lng == 77.5946
