# Edge Cases: Rate Limiting & Brute Force

The system implements automated rate limiting to prevent brute-force login attempts and protect the API from denial-of-service (DoS) attacks on the authentication layer.

## The Rate Limiting Engine

The system uses **Django REST Framework's Throttling** mechanism with a Redis backing store.

### Throttling Scenarios

- **Trigger**: A single IP address or user account exceeds a threshold of login attempts (e.g., 5 attempts in 1 minute).
- **Action**: The server returns `429 Too Many Requests`.
- **Lockout**: The account or IP is temporarily blocked (e.g., for 5-15 minutes).

### Brute-Force Prevention

- **Trigger**: Multiple failed login attempts are detected for a specific phone number or username.
- **Action**: The system incrementally increases the lockout time on subsequent failures to discourage automated scrapers and brute-force tools.

## The User Experience

Upon being rate-limited:
1. **Notification**: The user receives a message:"Too many login attempts. Please try again in $N$ minutes."
2. **Auth Lock**: No further authentication attempts are processed for that account until the timeout expires.

## Future Enhancements

- **Account Lockout (Hard Lockout)**: Implementing a"hard lockout"after a certain number of failed attempts (e.g., 10), requiring manual intervention via the support dashboard or a password reset link to unlock.
- **Anomaly Detection**: Using machine learning (ML) to identify and flag suspicious login patterns (e.g., logins from geographically distant locations within a short time frame).
- **IP-Based Throttling**: Implementing stricter rate limiting for IP addresses that exhibit suspicious behavior or are associated with known botnets.
