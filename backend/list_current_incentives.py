import os
import django
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.driver_incentives.models import DriverIncentive

incentives = DriverIncentive.objects.all().order_by('-created_at')

print("-" * 75)
print(f"{'TITLE':<25} | {'TYPE':<10} | {'REWARD':<10} | {'STATUS'}")
print("-" * 75)

if not incentives.exists():
    print("No driver incentives found in the database.")
else:
    for i in incentives:
        status = "✅ Active" if i.is_active and i.is_valid_now() else "❌ Inactive/Expired"
        print(f"{i.title[:25]:<25} | {i.type:<10} | ₹{i.reward_amount:<9} | {status}")

print("-" * 75)
print(f"Total Incentives: {incentives.count()}")
