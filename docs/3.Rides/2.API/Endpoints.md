# API Endpoints: Rides Module

The Rides API provides a comprehensive set of endpoints for riders, drivers, and admins.

## Rider Endpoints /api/rides/

|Method|Path|Description|
|:---|:---|:---|
|`POST`|`/request/`|Create a new ride request and start the matching process.|
|`GET`|`/active/`|Get details of the current active ride for the logged-in user.|
|`GET`|`/history/`|List past rides for the rider with summary data.|
|`GET`|`/estimate-fare/`|Get price estimates for different vehicle types (moto, go, xl).|
|`GET`|`/nearby-drivers/`|Fetch nearby drivers for UI markers (online drivers within 10km).|
|`PATCH`|`/<id>/cancel/`|Cancel a ride request (supports cancellation fees).|
|`POST`|`/<id>/feedback/`|Submit a rating (1-5) and comment after a completed trip.|
|`PATCH`|`/<id>/update-destination/`|Update the drop-off location while the ride is ongoing.|
|`GET`|`/<id>/fare-breakdown/`|Get an itemized list of fare components (base, dist, surge, wait).|
|`POST`|`/<id>/tip/`|Add a tip after the ride is completed.|

## Driver Endpoints /api/rides/

|Method|Path|Description|
|:---|:---|:---|
|`POST`|`/<id>/accept/`|Accept a ride offer (state: `OFFERED` -> `ASSIGNED`).|
|`POST`|`/<id>/reject/`|Decline a ride offer (moves to the next candidate).|
|`POST`|`/<id>/arrived/`|Mark that the driver has reached the pickup location.|
|`POST`|`/<id>/start/`|Start the ride by verifying the 4-digit OTP from the rider.|
|`POST`|`/<id>/complete/`|Finalize the ride at the destination (triggers fare calc).|
|`POST`|`/<id>/no-show/`|Mark the rider as a no-show (after waiting at pickup).|

## Admin Endpoints /api/rides/admin/

|Method|Path|Description|
|:---|:---|:---|
|`GET`|`/rides/`|Filterable list of all rides (live and historical).|
|`POST`|`/rides/actions/`|Bulk actions or manual overrides for ride states.|
|`GET`|`/fare-config/`|View/Edit global pricing parameters (base fare, per km, etc).|

## WebSocket Consumers

- **`RiderTrackingConsumer`**: `ws/rides/<ride_id>/`
- **`DriverLocationConsumer`**: `ws/tracking/driver-location/`
- **`DriverRidesConsumer`**: `ws/tracking/driver-rides/`
- **`AdminLiveMapConsumer`**: `ws/admin/live-map/`