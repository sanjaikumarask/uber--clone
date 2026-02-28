import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection

try:
    with connection.cursor() as cursor:
        cursor.execute("ALTER TABLE rides_ride ADD COLUMN city varchar(100) DEFAULT 'Chennai' NOT NULL;")
        cursor.execute("CREATE INDEX IF NOT EXISTS rides_ride_city_idx ON rides_ride (city);")
        print("Successfully added city column to rides_ride!")
except Exception as e:
    print(f"Failed: {e}")
