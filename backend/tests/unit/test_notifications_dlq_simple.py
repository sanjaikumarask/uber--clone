import pytest
from apps.notifications.services.dlq import send_to_dlq
from apps.notifications.models import Notification, NotificationDeadLetter
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.mark.django_db
def test_send_to_dlq_simple():
    user = User.objects.create(username="test_user_dlq")
    n = Notification.objects.create(user=user, type="TEST", channel="ws", payload={})
    send_to_dlq(n, "Test failure reason")
    
    assert NotificationDeadLetter.objects.filter(notification=n, reason="Test failure reason").exists()
