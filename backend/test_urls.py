import os

import django
from django.urls import Resolver404, resolve

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

paths = [
    "/api/drivers/ride-history/",
    "/api/payments/transactions/",
    "/api/drivers/me/",
]

for p in paths:
    try:
        match = resolve(p)
        print(f"✅ {p} -> {match.view_name}")
    except Resolver404:
        print(f"❌ {p} -> NOT FOUND")
