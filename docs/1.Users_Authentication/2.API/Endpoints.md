# API Endpoints: Users & Authentication

The Users API provides a complete set of endpoints for registration, login, profile management, and token refresh.

## User Endpoints /api/users/

|Method|Path|Description|
|:---|:---|:---|
|`POST`|`/register/`|Register a new user (`rider` or `driver`).|
|`POST`|`/login/rider/`|Login for riders with phone number/password.|
|`POST`|`/login/driver/`|Login for drivers with phone number/password.|
|`POST`|`/login/admin/`|Login for admins/operators.|
|`GET`|`/me/`|Get details of the currently logged-in user.|
|`POST`|`/token/refresh/`|Obtain a new access token using a refresh token.|
|`POST`|`/update-push-token/`|Update the `expo_push_token` for notifications.|

## Authentication Protocol

All authenticated requests must include the JWT token in the `Authorization` header:

```http
Authorization: Bearer <access_token>
```

## Response Structure

A successful login returns both user metadata and the JWT token pair:

```json
{
"access":"<access_token>",
"refresh":"<refresh_token>",
"user": {
"id": 1,
"phone":"+911234567890",
"role":"rider",
"first_name":"Sanjai",
"last_name":"Kumar"
}
}
```

## Errors

The API returns standard HTTP status codes for authentication scenarios:
- `401 Unauthorized`: Token is missing, invalid, or expired.
- `403 Forbidden`: User has a valid token but lacks the role for that view.
- `400 Bad Request`: Missing mandatory fields or invalid data structure.
