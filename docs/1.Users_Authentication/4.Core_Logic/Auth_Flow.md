# Authentication Flow: Uber Clone

The authentication flow is a multi-step sequence designed to verify a user's identity and Role before they can interact with the core ride-hailing functionality.

## The Primary Authentication Flow

The system uses a **Stateless Token-Based Flow**:

1. **Request Login**: The client (mobile/web) POSTs their phone number and password to the `/api/users/login/` endpoint.
2. **Verify Password**: The API server verifies the hash against the stored `User` record in PostgreSQL.
3. **Generate Tokens**: If valid, the server generates a JWT pair (access + refresh) identifying the user and their **Role** (`rider`, `driver`, `admin`).
4. **Issue Response**: The response includes both tokens and a subset of the user's profile metadata.
5. **Secure Requests**: The client includes the `access_token` in the `Authorization` header for all subsequent API calls.

## Multi-Role Login Support

The system implements role-specific login views for granular auditing and permission checks:

- **`RiderLoginView`**: Authenticates users with a `rider` role.
- **`DriverLoginView`**: Authenticates users with a `driver` role.
- **`AdminLoginView`**: Authenticates users with an `admin` or `operator` role.

## The User Identity Lifecycle

Every authenticated request undergoes the following transformation:

- **Incoming Header**: `Authorization: Bearer <token>`
- **JWT Middleware**: Validates the signature and expires the request if the token is invalid.
- **Request Population**: If valid, `request.user` is populated with the corresponding `User` model instance from the database.
- **Permission Guard**: The view's `permission_classes` are checked (e.g., `IsRider`, `IsDriver`) to ensure the user has the correct role.
