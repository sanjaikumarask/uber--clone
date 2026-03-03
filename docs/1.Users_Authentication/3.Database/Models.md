# Database Models: Users & Authentication

The custom `User` and `RiderStats` models form the core identity structure for the platform.

## The `User` Model

The `User` model tracks all participants and their permissions.

### Multi-Role Identification

|Field|Type|Description|
|:---|:---|:---|
|`username/email`|`CharField`|Standard identifies inherited from Django's `AbstractUser`.|
|`phone`|`CharField`|Unique phone number used as the primary identifier for riders and drivers.|
|`role`|`CharField`|A strict choice field: `rider`, `driver`, `admin`, or `operator`.|
|`is_staff` / `is_superuser`|`BooleanField`|Automatically set to `True` if `role =='admin'`, granting Django Admin access.|
|`expo_push_token`|`CharField`|Stored token for mobile push notifications (FCM/iOS).|

## The `RiderStats` Model

Every user with a `rider` role has an associated `RiderStats` record created for them.

### Performance & Tracking

- **`total_rides`**: Integer count of all successfully finished trips.
- **`avg_rating`**: Calculated average rating (1.0 to 5.0).
- **`rating_sum / count`**: Running counters used to update the `avg_rating` without re-scanning the entire feedback history.

## Audit Logic

The `User` model features a custom `save()` method that acts as a **Security Guard**:

```python
def save(self, *args, **kwargs):
if self.role == self.ROLE_ADMIN:
self.is_staff = True
self.is_superuser = True
else:
# Prevent non-admins from getting staff access accidentally
self.is_staff = False
self.is_superuser = False
super().save(*args, **kwargs)
```

This ensures that only users with an explicit `admin` role can access the Django admin dashboard.
