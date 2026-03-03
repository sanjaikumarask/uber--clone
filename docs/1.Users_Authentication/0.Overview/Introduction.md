# Introduction to Users & Authentication

The Users module is the foundation of identity within the Uber Clone. It ensures that every participant (Rider or Driver) is uniquely identified and authenticated before they can interact with the system's core services.

## Global Objectives

1. **Security**: Protect user accounts with robust passwords and secret-key-based JWT tokens.
2. **Identity Management**: Provide a clear distinction between different user roles (`rider`, `driver`, `admin`, `operator`).
3. **Scalability**: Use stateless JWT authentication to allow for horizontal scaling of the API servers.
4. **Real-time Reach**: Maintain up-to-date push tokens to ensure users receive critical notifications instantly.

## The Custom User Model

The system uses a custom `User` model inheriting from `AbstractUser`. Standard email/username fields are supplemented with:
- **Phone Number**: Primary identifier for many mobile use cases.
- **Role**: A strict choice field that dictates what parts of the system a user can access.
- **Is Staff/Superuser**: Automatically set based on the `admin` role to provide access to the Django backend.

## Authentication Strategy

The platform utilizes **SimpleJWT** for management:
- **Access Tokens**: Short-lived tokens used for every API request.
- **Refresh Tokens**: Long-lived tokens used to periodically rotate access tokens without forcing a re-login.
