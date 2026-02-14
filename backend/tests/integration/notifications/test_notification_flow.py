import pytest
from unittest.mock import patch, MagicMock
from apps.users.models import User
from apps.notifications.models import Notification
from apps.notifications.tasks import deliver_notification

@pytest.mark.django_db
@patch("apps.notifications.services.dispatcher.route_notification")
def test_notification_delivery_success(mock_route, client):
    # 1. Create Notif Pending
    user = User.objects.create_user(username="notify_me", email="a@b.com")
    notif = Notification.objects.create(
        user=user,
        channel="email",
        type="welcome",
        payload={"msg": "hi"},
        status="PENDING"
    )
    
    # 2. Execute Task Synchronously
    deliver_notification(notif.id)
    
    # 3. Verify Route Called
    mock_route.assert_called_once()
    
    # 4. Verify DB Update
    notif.refresh_from_db()
    assert notif.status == "SENT"
    assert notif.sent_at is not None

@pytest.mark.django_db
@patch("apps.notifications.services.dispatcher.route_notification")
@patch("apps.notifications.tasks.deliver_notification.apply_async")
def test_notification_retry_flow(mock_celery_retry, mock_route, client):
    user = User.objects.create_user(username="retry_me", email="a@b.com")
    notif = Notification.objects.create(
        user=user, channel="email", type="failed", payload={}, status="PENDING"
    )
    
    # Simulate Failure
    mock_route.side_effect = Exception("SMTP Down")
    
    deliver_notification(notif.id)
    
    notif.refresh_from_db()
    assert notif.retry_count == 1
    assert notif.status == "PENDING" # Still pending retry
    
    # Verify retry scheduled
    # Check checks apply_async call args
    mock_celery_retry.assert_called_once()
