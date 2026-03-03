# System Design: Users & Authentication

The architecture of the Users and Authentication system ensures secure and role-specific access to the platform's resources.

## Component Overview

The module consists of several decoupled parts:

1. **Custom User Model**: The central identity store in the PostgreSQL database.
2. **Auth API**: Views for registration and token generation.
3. **SimpleJWT Middleware**: Handles token validation and `request.user` population for every incoming request.
4. **Custom Permissions Layer**: Logic for enforcing role-specific access to certain API views.
5. **Push Token Store**: Real-time storage of `expo_push_token` for the Notifications module.

## Authentication Flow & Tokens

The platform utilizes **SimpleJWT** for stateless authentication:

- **Login Response**: Includes both `access` (short-lived) and `refresh` (long-lived) tokens.
- **Header Protocol**: Clients must send the access token in the `Authorization: Bearer <token>` header.
- **Renewal**: Clients use the `/token/refresh/` endpoint to obtain a new access token when the current one expires.

## Role-Based Access Control (RBAC)

The system enforces strict role-specific boundaries through the `role` field on the `User` model:

- **`rider`**: Can book rides, view their history, and provide feedback. Restricted from driver-specific views.
- **`driver`**: Can accept offers, update their location, and view earnings. Restricted from rider-only views.
- **`admin`**: Full access to the Django backend (`is_staff` and `is_superuser`).
- **`operator`**: Access to the Fleet Dashboard for system monitoring.
