from django.contrib.auth import get_user_model


class PhoneBackend:
    def authenticate(self, _request, username=None, password=None, **kwargs):
        phone = kwargs.get("phone") or username
        if phone is None:
            return None

        user_model = get_user_model()

        try:
            user = user_model.objects.get(phone=phone)
        except Exception:
            # Handle DoesNotExist or any DB failure gracefully
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

    def user_can_authenticate(self, user):
        is_active = getattr(user, "is_active", None)
        return is_active or is_active is None

    def get_user(self, user_id):
        user_model = get_user_model()
        try:
            return user_model.objects.get(pk=user_id)
        except user_model.DoesNotExist:
            return None
