from rest_framework.permissions import BasePermission


class IsRider(BasePermission):
    message = "Rider access only."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and getattr(user, "role", None) == "rider"
        )


class IsDriver(BasePermission):
    message = "Driver access only."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and getattr(user, "role", None) == "driver"
        )


class IsAdmin(BasePermission):
    message = "Admin access only."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and getattr(user, "role", None) == "admin"
        )
