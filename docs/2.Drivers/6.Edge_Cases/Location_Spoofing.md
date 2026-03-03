# Edge Cases: Location Spoofing detection

Location spoofing is a fraudulent practice where a driver uses third-party apps to fake their GPS coordinates, often to gain priority matching at high-demand"honey pots"(like airports) without being physically present.

## Detection Mechanisms

The system employs several layers of detection for GPS anomalies:

### Velocity Violation
- **Trigger**: The distance between two consecutive GPS pings (e.g. 5 seconds apart) implies a ground speed that is physically impossible (e.g., > 150 km/h in a city).
- **Action**: `abuse_detector.py` flags the driver record as"High Velocity Anomaly."

### Mock Provider Detection (Client-Side)
- **Trigger**: The mobile app detects that the"Allow Mock Locations"setting is enabled on the Android/iOS device.
- **Action**: The app refuses to send GPS pings and forces the driver record to `BLOCKED`.

### Stationary Honey-Potting
- **Trigger**: A driver is `ONLINE` and receiving offers at a high-demand location but shows **zero** jitter/noise in their GPS coordinates (perfectly identical precision for minutes). Real GPS sensors always have 1-3 meters of"noise."
- **Action**: Flagged as"Potential GPS Emulator."

## The Enforcement Workflow

When spoofing is detected:
1. **Immediate Purge**: The driver is removed from the Redis `drivers_geo` set.
2. **Reputation Drop**: The `trust_score` is heavily penalized (e.g., -50 points).
3. **Admin Alert**: The driver appears on the **Fraud Oversight Board** for immediate review.
4. **Suspension**: For repeated violations, the account is set to `is_suspended = True`.

