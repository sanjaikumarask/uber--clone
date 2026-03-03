# API Endpoints: Driver Incentives Module

The Driver Incentives API provides a secure and comprehensive set of endpoints for drivers and admins to manage their communication preferences and view history.

## Driver Endpoints /api/driver-incentives/

|Method|Path|Description|
|:---|:---|:---|
|`GET`|`/active/`|List all active and eligible incentives (Streak, Peak, Zone).|
|`GET`|`/progress/`|Get current personal progress for all active incentives.|
|`GET`|`/earnings/`|Get the full history of earned bonuses.|
|`POST`|`/opt-in/`|Mark specific (optional) incentives as `is_active = True`.|

## Admin & System Endpoints

|Method|Path|Description|
|:---|:---|:---|
|`POST`|`/admin/create-incentive/`|Configure a new incentive rule (Type, Condition, Timeframe).|
|`GET`|`/admin/stats/`|Dashboard for monitoring aggregate incentive payouts and performance.|
|`POST`|`/admin/bulk-incentive/`|Deploy a bonus to all online drivers in a specific city.|

## Live Progress Interaction

Drivers can track their live progress on the **Earnings** screen in their mobile app:

**Progress Payload Example:**
```json
{
"incentive_id": 42,
"title":"Evening Rush Streak",
"type":"STREAK",
"current_count": 3,
"rides_required": 5,
"reward":"₹100.00",
"is_completed": false
}
```

The system uses these updates to refresh the **Driver Interface** and provide real-time feedback after every completed ride.
- **WebSocket Integration**: The driver app is notified immediately upon an incentive's completion and payout.
