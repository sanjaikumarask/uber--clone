Build a complete production-grade Offers + Driver Incentive System for a ride-hailing platform using Django + DRF.

Do NOT give high-level explanations. Provide clean, working, scalable code.

========================

1. SYSTEM OVERVIEW
   ========================
   Implement 3 connected systems:

2. Rider Offer Engine

3. Driver Incentive Engine

4. Admin Dashboard Control Panel

All systems must be integrated with Ride lifecycle and Payment system.

========================
2. RIDER OFFER ENGINE
=====================

Implement:

Model: Offer

* code
* discount_type (FLAT / PERCENTAGE)
* value
* max_discount
* min_ride_value
* usage_limit
* per_user_limit
* valid_from
* valid_to
* is_active

Flow:

* Fetch active offers
* Validate offer on apply
* Apply discount to fare
* Mark offer used after ride completion

APIs:

* GET /offers/active/
* POST /offers/apply/
* POST /offers/validate/

Edge cases:

* expired offers
* usage limit exceeded
* invalid code
* multiple offers conflict

========================
3. DRIVER INCENTIVE ENGINE
==========================

Implement:

Model: DriverIncentive

* type (STREAK / PEAK / ZONE)
* condition (JSON)
* reward_amount
* max_per_day
* valid_from
* valid_to
* is_active

Track driver progress using Redis or DB.

Incentive types:

1. STREAK:
   complete N rides → reward

2. PEAK:
   rides in time window → reward

3. ZONE:
   rides inside geo area → reward

Flow:

* On ride completion:
  → check active incentives
  → update progress
  → if condition met:
  → credit driver wallet (LedgerEntry)
  → reset progress if needed

Anti-abuse:

* minimum distance
* minimum duration
* no fake/self rides
* max rewards per day

========================
4. ADMIN DASHBOARD
==================

Build APIs for admin to:

Offers:

* create / update / deactivate offers
* set limits and rules

Incentives:

* create / update / deactivate incentives
* define conditions (rides_required, time_range, geo_zone)

Monitoring:

* total discounts given
* total incentives paid
* usage analytics

========================
5. INTEGRATION WITH RIDE FLOW
=============================

Hook into:

Ride Completion:

* apply offer usage
* trigger incentive engine

Fare Calculation:

* apply discount before final fare

Payment:

* ensure correct final payable amount

========================
6. DATA FLOW
============

Rider:

* request ride → apply offer → discounted fare → complete ride → mark usage

Driver:

* complete ride → incentive engine → reward wallet

Admin:

* configures rules → system executes automatically

========================
7. OUTPUT REQUIREMENTS
======================

Provide:

1. models.py (Offer, DriverIncentive)
2. services:

   * offer_engine.py
   * incentive_engine.py
3. Redis usage for streak tracking
4. APIs (views + serializers)
5. Admin endpoints
6. Integration points in ride lifecycle
7. Edge case handling

========================
IMPORTANT
=========

* Must be scalable
* Must prevent abuse
* Must avoid race conditions
* Must be modular
* No pseudo code
* No shortcuts   how much time to do theseimport os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

def inspect_table(table_name):
    print(f"\nInspecting table: {table_name}")
    try:
        with connection.cursor() as cursor:
            # PostgreSQL specific query to get columns
            cursor.execute(f"""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = '{table_name}'
                ORDER BY column_name;
            """)
            columns = cursor.fetchall()
            if not columns:
                print(f"Table '{table_name}' not found or has no columns.")
            for col in columns:
                print(f" - {col[0]} ({col[1]})")
    except Exception as e:
        print(f"Error inspecting {table_name}: {e}")

inspect_table('rides_ride')
inspect_table('offers_offer')
inspect_table('driver_incentives_driverincentive')
