# Trust Score & Performance Engine

The Trust Score is an algorithmic representation of a driver's reliability and reputation on the platform. It directly impacts their `Level` and priority in the matching process.

## The Trust Score Formula

The `trust_score` (0-100) is a weighted metric adjusted in real-time based on driver actions.

### Positive Impacts (+)
- **Completed Rides**: Successful trips with high rider ratings.
- **Active Hours**: Consistency in being ONLINE during peak hours.
- **Longevity**: History of being on the platform without major incidents.

### Negative Impacts (-)
- **Cancellations**: Penalties for cancelling an accepted ride (e.g., -5 points).
- **Low Acceptance Rate**: Frequent rejections of ride offers.
- **Fraud Flags**: Serious drops for rides flagged by the fraud detection service (e.g., -20 points).
- **Poor Ratings**: Consistent 1-2 star feedback from riders.

## Driver Levels & Benefits

Trust scores determine the driver's level progression:

- **Normal**: Initial entry.
- **Active**: Consistent performance.
- **Consistent**: High trust score and high ride count.
- **Pro**: Top 5% of drivers. Receive priority in matching and potential lower platform commissions.

## Auto-Suspension

If a driver's `trust_score` falls below a critical threshold (e.g., < 40), the system:
1. **Alerts Admin**: Flagged for manual account review.
2. **Auto-Suspends**: Sets `is_suspended = True` and moves status to `BLOCKED`.
3. **Notifications**: Informs the driver that they must contact support to regain access.

## Performance Audit

Level calculation is handled by the `level_engine.py` service, which runs periodically via Celery. This ensures that a driver's level reflects their **current** behavior rather than historical averages.
