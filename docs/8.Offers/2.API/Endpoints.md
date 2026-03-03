# API Endpoints: Offers & Promotions Module

The Offers API provides a secure and comprehensive set of endpoints for riders and admins to manage their communication preferences and view history.

## Rider Endpoints /api/offers/

|Method|Path|Description|
|:---|:---|:---|
|`GET`|`/active/`|List all active and eligible offers (Flat, Percentage, Zone).|
|`POST`|`/apply/`|Apply a promo code to a specific ride booking.|
|`GET`|`/history/`|List the current user's history of used promo codes.|
|`GET`|`/validate/`|Check code validity and get the estimated discount for a ride.|

## Admin & System Endpoints /api/admin/offers/

|Method|Path|Description|
|:---|:---|:---|
|`POST`|`/create/`|Configure a new offer rule (Code, Type, Value, Constraints).|
|`GET`|`/stats/`|Dashboard for monitoring aggregate offer usage and performance.|
|`PATCH`|`/<id>/deactivate/`|Manually deactivate a specific promotional campaign.|

## Live Application Interaction

Riders can apply a promo code during the ride booking process:

**Validation Payload Example:**
```json
{
"code":"UBERNEW50",
"ride_id": 42
}
```

The system uses these updates to refresh the **Fare Estimate** and provide real-time feedback to the rider.
- **Validation Response**: Includes the calculated `discount_applied` and the `final_estimated_fare`.
