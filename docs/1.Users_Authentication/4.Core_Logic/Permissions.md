# Custom Permissions: Role-Based Access Control

The platform uses a custom Permission Layer on top of Django REST Framework to ensure strict role-based access control (RBAC) to the API views.

## The Permissions Engine

The permissions engine works together with the `role` field on the `User` model.

### Custom Roles Definitions

- **`IsRider`**: Grants access only if `request.user.role =='rider'`.
- **`IsDriver`**: Grants access only if `request.user.role =='driver'`.
- **`IsAdmin`**: Grants access only if `request.user.role =='admin'` (equivalent to `is_staff` or `is_superuser`).
- **`IsOperator`**: Grants access for the Fleet Dashboard (`role =='operator'`).

## Guarding the API Views

Permissions are applied to the API views to ensure that only authorized users can access specific functionality:

```python
class CreateRideView(APIView):
permission_classes = [IsAuthenticated, IsRider]
# ...
```

This prevents a driver from accidentally (or maliciously) attempting to book a ride for themselves or another user.

## The Middleware Flow

The permission check is the final gatekeeper before a view's logic is executed:

1. **Incoming Request**: A client calls an API endpoint.
2. **JWT Middleware**: Verifies the signature and populates `request.user`.
3. **Authentication Guard**: `IsAuthenticated` ensures the user is logged in.
4. **Role Guard**: The role-specific permission (e.g., `IsRider`) checks that the `role` field on the `User` model matches the view's requirements.
5. **Logic Execution**: Only if all permission checks pass, the view's internal logic is executed.

## Efficiency & Performance

- **Role-Specific Views**: By using role-specific login views (e.g., `RiderLoginView`), the system can audit logins and handle role-specific onboarding flows independently.
- **Auditing**: Every permission check is recorded in the system logs for security auditing.
- **No Extra DB Hits**: The `role` field is a core attribute of the `User` model, ensuring that permission checks do not require additional database queries.
