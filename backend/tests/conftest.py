import pytest
from django.conf import settings
from decimal import Decimal
from apps.payments.models import LedgerEntry

@pytest.fixture
def user(db, django_user_model):
    return django_user_model.objects.create_user(
        username="5555555555",
        phone="5555555555",
        password="password",
        role="rider"
    )

@pytest.fixture
def driver(db, django_user_model):
    return django_user_model.objects.create_user(
        username="6666666666",
        phone="6666666666",
        password="password",
        role="driver"
    )

@pytest.fixture
def platform_user(db, django_user_model):
    # Ensure platform user exists with ID from settings
    user, _ = django_user_model.objects.get_or_create(
        id=settings.PLATFORM_USER_ID,
        defaults={
            "username": "0000000000",
            "phone": "0000000000",
            "password": "password",
            "role": "admin"
        }
    )
    return user
