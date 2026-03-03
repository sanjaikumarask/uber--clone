# API Endpoints: Notifications Module

The Notifications API provides a secure set of endpoints for riders, drivers, and admins to manage their communication preferences and view history.

## Rider & Driver Endpoints /api/notifications/

|Method|Path|Description|
|:---|:---|:---|
|`GET`|`/history/`|List the current user's last 50 notifications (Push, SMS).|
|`GET`|`/unread-count/`|Get the count of unread (new) notifications.|
|`PATCH`|`/<id>/mark-read/`|Update a specific notification as `is_read = True`.|
|`GET`|`/preferences/`|Get current notification channel preferences.|
|`PATCH`|`/preferences/`|Enable/Disable specific channels (Push, Email, SMS).|

## Admin & System Endpoints

|Method|Path|Description|
|:---|:---|:---|
|`POST`|`/admin/broadcast/`|Send a push notification to all online drivers (e.g. for maintenance).|
|`GET`|`/admin/logs/`|Detailed list of all notification statuses and failure reasons.|
|`GET`|`/admin/dlq/`|Monitor permanently failed notifications in the Dead Letter Queue.|

## Live Event Protocol

System components (e.g., Rides, Payments) trigger notifications via an internal service:

**Service Call Example:**
```python
from apps.notifications.models import Notification

Notification.objects.create(
user=rider_user,
channel="push",
type="RIDE_CANCELLED",
payload={
"title":"Ride Cancelled",
"body":"Your driver has cancelled the ride. We are finding a new one...",
"ride_id": 42
}
)
```

The system automatically dispatches this to a **Celery Worker** for asynchronous delivery and keeps an audit record in the database.
