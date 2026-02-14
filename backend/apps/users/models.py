from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_RIDER = "rider"
    ROLE_DRIVER = "driver"
    ROLE_ADMIN = "admin"

    ROLE_CHOICES = (
        (ROLE_RIDER, "Rider"),
        (ROLE_DRIVER, "Driver"),
        (ROLE_ADMIN, "Admin"),
    )

    phone = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,  # ← IMPORTANT to avoid createsuperuser crash
    )

    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default=ROLE_RIDER,
    )

    def save(self, *args, **kwargs):
        # 🔥 HARD RULE: admin role must be staff
        if self.role == self.ROLE_ADMIN:
            self.is_staff = True
            self.is_superuser = True
        super().save(*args, **kwargs)

    @property
    def is_rider(self):
        return self.role == self.ROLE_RIDER

    @property
    def is_driver(self):
        return self.role == self.ROLE_DRIVER

    @property
    def is_admin(self):
        return self.role == self.ROLE_ADMIN or self.is_superuser
