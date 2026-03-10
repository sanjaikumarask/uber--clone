import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import User

# Get any admin user
user = User.objects.filter(is_superuser=True).first()
if not user:
    print("No admin user found!")
else:
    token = str(RefreshToken.for_user(user).access_token)
    print("Token length:", len(token))

    jwt_auth = JWTAuthentication()
    try:
        validated_token = jwt_auth.get_validated_token(token)
        print("Valid token!")
        u = jwt_auth.get_user(validated_token)
        print("User extracted:", u.username)
    except Exception as e:
        print("Error validating:", e)
