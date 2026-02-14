from django.contrib.auth import get_user_model

class PhoneBackend:
    def authenticate(self, request, username=None, password=None, **kwargs):
        phone = kwargs.get('phone') or username
        if phone is None:
            return None

        User = get_user_model()

        try:
            user = User.objects.get(phone=phone)
        except User.DoesNotExist:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

    def user_can_authenticate(self, user):
        is_active = getattr(user, 'is_active', None)
        return is_active or is_active is None

    def get_user(self, user_id):
        User = get_user_model()
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
