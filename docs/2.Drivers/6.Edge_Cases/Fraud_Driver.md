# Edge Cases: Driver Fraud Detection

The system uses automated background analysis to identify and flag driver fraud, ensuring financial and operational integrity.

## Fraud Scenarios

The `abuse_detector.py` service monitors for several types of driver-side fraud:

### Distance Inflation (Fare Manipulation)
- **Trigger**: The `actual_distance_km` is significantly higher (> 150%) than the `planned_distance_km` on a completed ride, with no legitimate stops or detours.
- **Action**: `is_fraud_flagged = True`.
- **Penalty**: Payout to the driver is delayed for 24-48 hours.

### Payout Poaching (Ghost Riding)
- **Trigger**: A driver starts and completes a ride with a suspiciously low `actual_distance_km` (e.g., < 0.5 km) multiple times in a single day.
- **Reason**: Often used to collect minimum fare or referral bonuses without actually driving.
- **Action**: flagged in the system for admin review.

### Account Sharing (Device Anomalies)
- **Trigger**: Multiple drivers using the same device or one driver using multiple accounts simultaneously from the same IP address.
- **Action**: `is_suspended = True` for all accounts.

## Enforcement and Recovery

When a driver is flagged for fraud:
1. **Trust Score Drop**: Significant penalty to their reputation score.
2. **Support Screen Lock**: A banner appears on the driver app:"Your account is under review for policy violations."
3. **Financial Audit**: The **Ledger Reconciliation** service marks all recent driver credit entries as `PENDING_REVIEW` to prevent external withdrawal.
