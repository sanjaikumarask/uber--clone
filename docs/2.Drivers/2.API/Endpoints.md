# API Endpoints: Drivers Module

The Drivers API handles onboarding, document submission, real-time status management, and performance analytics.

## Driver Endpoints /api/drivers/

|Method|Path|Description|
|:---|:---|:---|
|`POST`|`/register/`|Create a new driver profile (linked to a User).|
|`GET`|`/me/`|Get current driver profile, level, and stats.|
|`PATCH`|`/update-status/`|Toggle between `ONLINE` and `OFFLINE` (requires verification).|
|`POST`|`/location/`|Update real-time GPS coordinates (updates Redis and DB).|
|`GET`|`/stats/`|Get detailed performance metrics (Trust Score, Acceptance Rate).|
|`GET`|`/documents/`|List current document statuses.|
|`POST`|`/documents/upload/`|Upload verification documents (License, RC, etc).|

## Admin Endpoints (Drivers)

|Method|Path|Description|
|:---|:---|:---|
|`GET`|`/admin/drivers/`|List all drivers with filters (status, level, verification).|
|`POST`|`/admin/docs/<doc_id>/approve/`|Approve a specific document.|
|`POST`|`/admin/docs/<doc_id>/reject/`|Reject a specific document with a reason.|
|`POST`|`/admin/drivers/<id>/override-level/`|Manually set a driver's level (e.g. for testing or promotion).|

## Live Location Protocol

Drivers should update their location every **5-10 seconds** while `ONLINE`. 

**Request Payload:**
```json
{
"lat": 13.0827,
"lng": 80.2707
}
```

The system uses these updates to refresh the **Redis GEOSPATIAL** index and provide real-time tracking to riders.
