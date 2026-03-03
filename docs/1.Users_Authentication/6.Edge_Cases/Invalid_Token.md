# Edge Cases: Invalid & Expired Tokens

The authentication system is designed to handle invalid, malformed, and expired JWT tokens gracefully to ensure system security and a consistent user experience.

## Disruption Scenarios

The system encounters"Disrupted Credentials"in the following scenarios:

### Expired Token (`exp` claim)

- **Trigger**: The `access_token` expiration timestamp has passed.
- **Action**: The server returns `401 Unauthorized` with a specific `token_not_valid` code.
- **Resolution**: The client app catches this error and initiates the [**Token Refresh Workflow**](../5.Workflows/Token_Refresh.md) automatically.

### Malformed Token (Tampering)

- **Trigger**: The incoming token's signature does not match the server's secret key, or the JSON structure is invalid.
- **Action**: The server returns `401 Unauthorized`.
- **Resolution**: The client app immediately logs the user out and clears all stored credentials to protect against session hijacking.

### Blacklisted Token (Logout)

- **Trigger**: A user explicitly logs out, and their `refresh_token` is added to the system-wide blacklist.
- **Action**: Any subsequent attempt to use that refresh token is rejected with a `401 Unauthorized`.

## The Recovery Lifecycle

The client app (e.g., React Native/Next.js) handles these edge cases using **Interceptors**:

1. **Response Interceptor**: Monitors all outgoing responses for `401` status.
2. **Queue & Retry**: If a `401` is detected due to expiration, the app pauses other pending requests, refreshes the token, and then retries the failed call with the new credential.
3. **Terminal Logout**: If the refresh also fails, the user is redirected to the `/login` screen.
