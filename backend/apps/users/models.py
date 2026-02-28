from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_RIDER = "rider"
    ROLE_DRIVER = "driver"
    ROLE_ADMIN = "admin"
    ROLE_OPERATOR = "operator"

    ROLE_CHOICES = (
        (ROLE_RIDER, "Rider"),
        (ROLE_DRIVER, "Driver"),
        (ROLE_ADMIN, "Admin"),
        (ROLE_OPERATOR, "Dashboard Operator"),
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

    expo_push_token = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Expo push token for mobile notifications"
    )

    def save(self, *args, **kwargs):
        # 🔥 HARD RULE: admin role must be staff, others MUST NOT be staff
        if self.role == self.ROLE_ADMIN:
            self.is_staff = True
            self.is_superuser = True
        else:
            # Prevent non-admins from accessing Django backend
            self.is_staff = False
            self.is_superuser = False
            
        super().save(*args, **kwargs)

    @property
    def is_rider(self):
        return self.role == self.ROLE_RIDER

    @property
    def is_driver(self):
        return self.role == self.ROLE_DRIVER

    @property
    def is_admin(self):
        # 🔑 Dashboard separation:
        # ROLE_OPERATOR is for the Fleet Dashboard.
        # ROLE_ADMIN is for the Django Backend.
        return self.role == self.ROLE_OPERATOR or self.is_superuser

class RiderStats(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="rider_stats",
    )
    total_rides = models.PositiveIntegerField(default=0)
    rating_sum = models.PositiveIntegerField(default=0)
    rating_count = models.PositiveIntegerField(default=0)
    avg_rating = models.FloatField(default=5.0)

    updated_at = models.DateTimeField(auto_now=True)

    def update_rating(self, rating: int):
        self.rating_sum += int(rating)
        self.rating_count += 1
        self.avg_rating = round(self.rating_sum / self.rating_count, 2)
        self.save(update_fields=["rating_sum", "rating_count", "avg_rating", "updated_at"])

    def __str__(self):
        return f"RiderStats for {self.user.phone} ({self.avg_rating})"
