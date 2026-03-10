import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from apps.users.models import User
print("Creating user...")
try:
    u = User.objects.create_user(username="test_driver_xyz", role="driver")
    print(u.driver)
except Exception as e:
    import traceback
    traceback.print_exc()
