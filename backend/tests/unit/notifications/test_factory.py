import pytest
from unittest.mock import patch, MagicMock
from apps.notifications.services.factory import create_and_enqueue_notification
from apps.notifications.models import Notification

@pytest.mark.django_db
class TestNotificationFactory:
    @patch('apps.notifications.tasks.deliver_notification.delay')
    def test_create_and_enqueue_notification_success(self, mock_delay):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.create(username="testuser")
        
        user_id = user.id
        event_type = 'RIDE_COMPLETED'
        channel = 'ws'
        payload = {'ride_id': 1}
        
        create_and_enqueue_notification(
            user_id=user_id,
            event_type=event_type,
            channel=channel,
            payload=payload
        )
        
        notification = Notification.objects.last()
        assert notification is not None
        assert notification.user_id == user_id
        assert notification.type == event_type
        assert notification.channel == channel
        assert notification.payload == payload
        
        # The task is called in factory and in model.save.
        # So it should be called at least once.
        assert mock_delay.called

    @patch('apps.notifications.tasks.deliver_notification.delay')
    def test_create_and_enqueue_notification_invalid_data_missing_fields(self, mock_delay):
        # Missing payload should raise TypeError
        with pytest.raises(TypeError):
            create_and_enqueue_notification(
                user_id=1,
                event_type="TEST",
                channel="WS"
            )
