import pytest
from unittest.mock import patch
from apps.notifications.services.factory import create_and_enqueue_notification
from apps.notifications.models import Notification
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.mark.django_db
def test_create_and_enqueue_notification_simple():
    user = User.objects.create(username="factory_user", phone="1234567890")
    with patch("apps.notifications.services.factory.deliver_notification") as mock_deliver:
        create_and_enqueue_notification(
            user_id=user.id,
            event_type="TEST_EVENT",
            channel="email",
            payload={"msg": "hello"}
        )
        assert Notification.objects.filter(type="TEST_EVENT").exists()
        mock_deliver.delay.assert_called_once()
