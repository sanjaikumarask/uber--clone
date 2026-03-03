# API Endpoints: Support & Safety Module

The Support API handles high-frequency coordinate submission and real-time location retrieval.

## Rider Endpoints /api/support/

|Method|Path|Description|
|:---|:---|:---|
|`GET`|`/faqs/`|List all active FAQs (filtered by `audience: RIDER`).|
|`POST`|`/tickets/`|Create a new support ticket (linked to a `ride_id`).|
|`GET`|`/tickets/history/`|View current user's history of tickets and their statuses.|
|`POST`|`/emergency/sos/`|Trigger an SOS/Emergency alert during an active ride.|

## Driver Endpoints /api/support/

|Method|Path|Description|
|:---|:---|:---|
|`GET`|`/faqs/`|List all active FAQs (filtered by `audience: DRIVER`).|
|`POST`|`/tickets/`|Create a support ticket related to a ride or account issue.|
|`POST`|`/emergency/sos/`|Trigger an SOS/Emergency alert while on a ride.|

## Admin Endpoints (Support)

|Method|Path|Description|
|:---|:---|:---|
|`GET`|`/admin/tickets/list/`|Comprehensive list of all open tickets.|
|`PATCH`|`/admin/tickets/<id>/resolve/`|Resolve or Reject a specific support ticket.|
|`GET`|`/admin/emergencies/active/`|Firehose endpoint for monitoring all active SOS alerts.|
|`PATCH`|`/admin/emergencies/<id>/resolve/`|Mark an SOS alert as `RESOLVED` or `FALSE_ALARM`.|

## Live Emergency Protocol

When an SOS is triggered (`/emergency/sos/`):

**Request Payload:**
```json
{
"ride_id": 42,
"lat": 13.0827,
"lng": 80.2707,
"description":"Possible misconduct / safety risk"
}
```

The system immediately creates an `Emergency` record, captures the GPS snapshot, and broadcasts a high-priority alert to the **Admin Dashboard** via WebSockets.
- **Validation**: Must be an active ride to trigger an SOS for safety.
- **Notification**: Admins are immediately alerted with the driver/rider details and the ride's current location on the map.
