# JWT System: Authentication Mechanism

The platform uses a JSON Web Token (JWT) system backed by `SimpleJWT` for stateless authentication and session management.

## The JWT Pattern

The platform supports two types of tokens:

1. **Access Token**: Short-lived (e.g., 60 minutes) token sent with every API request.
2. **Refresh Token**: Long-lived (e.g., 24 hours) token used to get a new access token without re-authenticating.

## Token Structure

Tokens are signed with a server-side secret and contain user metadata:
- `user_id`: Numeric identifier of the logged-in user.
- `role`: The user's role (`rider`, `driver`, `admin`).
- `exp`: Expiration timestamp.

## Verification Logic

The platform implements a **JWT Authentication Backend**:

```python
AUTHENTICATION_BACKENDS = [
'django.contrib.auth.backends.ModelBackend',
'rest_framework_simplejwt.authentication.JWTAuthentication',
]
```

- Every request to a protected API view is intercepted by the **JWTAuthentication Middleware**.
- The middleware validates the token signature and expiration.
- If valid, it populates `request.user` with the corresponding `User` model instance from the database.
