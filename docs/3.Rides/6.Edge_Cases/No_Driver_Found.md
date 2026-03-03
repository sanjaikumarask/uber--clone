# Edge Cases: No Driver Found

The"No Driver Found"scenario occurs when the matching engine exhausts its supply of candidates without a successful assignment.

## The Search Lifecycle

The matching engine attempts to find a driver over multiple cycles:

1. **Initial Search**: 10 km radius, top 20 candidates.
2. **Sequential Offering**: Each candidate gets a 60-second window to accept.
3. **Search Exhaustion**: If all candidate drivers reject or time out, the `search_attempt` count is incremented.

### When"No Driver"is Triggered

The system officially marks a ride as `CANCELLED` (with `SYSTEM` as the reason) under two conditions:

- **Cycle Limit**: No driver is found after **3 complete search cycles**.
- **Time Limit**: The ride has been in `SEARCHING` state for more than **5 minutes**.

## The Rider Experience

1. **Status: `SEARCHING`**: The rider sees a"Searching for drivers"message.
2. **Notification**:"We're experiencing high demand and haven't found a driver yet. We're still looking!"
3. **Terminal Message**:"Sorry, we couldn't find a driver for your request. Please try again soon."

## The System Resolution

When no driver is found:
- **Ledger Reconciliation**: The system ensures no charges are pending for the rider.
- **Supply Analysis**: The failure event is logged for **Demand Heatmap Analysis**, helping the operations team identify areas with low driver supply.
- **Retry Strategy**: Riders are encouraged to"Retry"but may be offered a surge multiplier price to attract more drivers to the area.
