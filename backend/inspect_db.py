import os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

def inspect_table(table_name):
    print(f"\nInspecting table: {table_name}")
    try:
        with connection.cursor() as cursor:
            # PostgreSQL specific query to get columns
            cursor.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = %s
                ORDER BY column_name;
            """, [table_name])
            columns = cursor.fetchall()
            if not columns:
                print(f"Table '{table_name}' not found or has no columns.")
            for col in columns:
                print(f" - {col[0]} ({col[1]})")
    except Exception as e:
        print(f"Error inspecting {table_name}: {e}")

if __name__ == "__main__":
    inspect_table('rides_ride')
    inspect_table('offers_offer')
    inspect_table('driver_incentives_driverincentive')
