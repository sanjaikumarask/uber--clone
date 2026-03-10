import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

username = os.getenv("ADMIN_USERNAME", "admin")
password = os.getenv("ADMIN_PASSWORD", "admin123")
email = os.getenv("ADMIN_EMAIL", "admin@uber.com")

if not User.objects.filter(username=username).exists():
    print(f"Creating superuser '{username}'...")
    User.objects.create_superuser(username=username, email=email, password=password)
    # Ensure role is set correctly if using custom user model logic
    u = User.objects.get(username=username)
    if hasattr(u, "role"):
        u.role = "admin"  # Assuming 'admin' is the value for admin role
        u.save()
    print("✅ Admin user created successfully!")
    print(f"Username: {username}")
    print(f"Password: {password}")
else:
    print(f"User '{username}' already exists. Updating password...")
    u = User.objects.get(username=username)
    u.set_password(password)
    if hasattr(u, "role"):
        u.role = "admin"
    u.is_staff = True
    u.is_superuser = True
    u.save()
    print("✅ Admin user updated!")
    print(f"Username: {username}")
    print(f"Password: {password}")
