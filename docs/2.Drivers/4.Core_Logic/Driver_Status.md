# Driver Status Logic

The `Status` field on the `Driver` model is a server-authoritative state that dictates availability for ride matching.

## The Status Finite State Machine (FSM)

The system enforces valid transitions to prevent inconsistencies.

|State|Allowed Transitions To|Logic|
|:---|:---|:---|
|`OFFLINE`|`ONLINE`|Driver enters the marketplace. **Requires `is_verified=True`**.|
|`ONLINE`|`BUSY`, `OFFLINE`|Available for matching.|
|`BUSY`|`ONLINE`|Currently on a ride. Reverts to `ONLINE` upon ride completion.|
|`BLOCKED`|`OFFLINE`|Admin-enforced lockout (suspended).|

## Verification Gate

A driver **cannot** go `ONLINE` unless they have passed the verification process. 

```python
def transition_to(self, new_status):
if not self.is_verified and new_status == self.Status.ONLINE:
raise ValidationError("Unverified drivers cannot go ONLINE.")
# ...
```

## Redis Synchronization

When a status changes:
1. **DB Commit**: The status is saved in PostgreSQL.
2. **Redis Pruning**: If a driver goes `OFFLINE` or `BUSY`, they are removed from the Redis GEOSPATIAL index to ensure they don't receive new offers.
3. **Real-time Broadcast**: The change is pushed to the Admin Dashboard (Live Map) to update the driver's icon.

## Rejection Cooldown

If a driver's rejection count reaches the daily limit, they are not moved to a different status, but their matching behavior changes (Auto-Assignment), as discussed in the [**Matching Engine documentation**](../../3.Rides/4.Core_Logic/Matching_Engine.md).
