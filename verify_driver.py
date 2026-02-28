import os
import sys
import django

# Set up Django environment
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.users.models import User
from apps.drivers.models import Driver, DriverDocument

def verify_driver(phone):
    try:
        user = User.objects.get(phone=phone)
        if not hasattr(user, 'driver'):
            print(f"Error: User with phone {phone} is not a driver.")
            return
        
        driver = user.driver
        
        # 1. Force is_verified to True
        driver.is_verified = True
        driver.save()
        
        # 2. Also approve any pending documents to stay consistent
        pending_docs = DriverDocument.objects.filter(driver=driver, status=DriverDocument.Status.PENDING)
        for doc in pending_docs:
            doc.status = DriverDocument.Status.APPROVED
            doc.save()
            
        print(f"✅ Driver {phone} (ID: {driver.id}) has been manually VERIFIED.")
        print("They can now go ONLINE in the driver app.")
        
    except User.DoesNotExist:
        print(f"Error: No user found with phone {phone}.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python verify_driver.py <phone_number>")
        sys.exit(1)
    
    phone_num = sys.argv[1]
    verify_driver(phone_num)
