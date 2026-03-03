import pytest
from django.conf import settings
from decimal import Decimal
from apps.payments.models import LedgerEntry

@pytest.fixture
def user(db, django_user_model):
    import random
    phone = f"+919{random.randint(100000000, 999999999)}"
    user = django_user_model.objects.create_user(
        username=phone,
        phone=phone,
        password="password",
        role="rider"
    )
    return user

@pytest.fixture
def platform_user(db, django_user_model):
    from django.conf import settings
    user, _ = django_user_model.objects.get_or_create(
        id=settings.PLATFORM_USER_ID,
        defaults={
            "username": "platform_admin",
            "phone": "+910000000000",
            "role": "admin",
            "is_staff": True
        }
    )
    return user

@pytest.fixture
def driver_user(db, django_user_model):
    from apps.drivers.models import Driver
    import random
    phone = f"+918{random.randint(100000000, 999999999)}"
    user = django_user_model.objects.create_user(
        username=phone,
        phone=phone,
        password="password",
        role="driver"
    )
    # The signal apps.users.signals.create_driver_profile might have created it already
    driver, _ = Driver.objects.update_or_create(
        user=user,
        defaults={
            "status": Driver.Status.OFFLINE,
            "is_verified": True,
            "vehicle_model": "Tesla Model S",
            "vehicle_number": f"KA01-UBER-{random.randint(1000, 9999)}"
        }
    )
    return user

@pytest.fixture
def ride(db, user):
    from apps.rides.models import Ride
    return Ride.objects.create(
        rider=user,
        pickup_lat=12.9716,
        pickup_lng=77.5946,
        drop_lat=12.9352,
        drop_lng=77.6245,
        status="SEARCHING"
    )

@pytest.fixture
def api_client():
    from rest_framework.test import APIClient
    return APIClient()

@pytest.fixture
def auth_client(api_client, user):
    from rest_framework_simplejwt.tokens import AccessToken
    token = AccessToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return api_client

@pytest.fixture
def driver_client(api_client, driver_user):
    from rest_framework_simplejwt.tokens import AccessToken
    token = AccessToken.for_user(driver_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return api_client

@pytest.fixture(autouse=True)
def clear_test_cache():
    from django.core.cache import cache
    cache.clear()

@pytest.fixture(autouse=True)
def disable_notifications(monkeypatch):
    """Prevent real notification delivery during tests"""
    from apps.notifications.tasks import deliver_notification
    monkeypatch.setattr("apps.notifications.tasks.deliver_notification.delay", lambda *a, **k: None)
    monkeypatch.setattr("apps.notifications.tasks.deliver_notification.apply_async", lambda *a, **k: None)
