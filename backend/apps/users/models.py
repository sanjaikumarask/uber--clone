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
        blank=True,
        default="",
        help_text="Expo push token for mobile notifications",
    )

    provider = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="google, facebook, apple, etc.",
    )

    # Profile fields
    gender = models.CharField(max_length=20, blank=True, default="")
    address = models.TextField(blank=True, default="")
    referral_code = models.CharField(max_length=20, unique=True, null=True, blank=True)
    referred_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='referrals')


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

    @property
    def is_online(self):
        if hasattr(self, 'driver'):
            return self.driver.status == "ONLINE"
        return False


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

    def __str__(self):
        return f"RiderStats for {self.user.phone} ({self.avg_rating})"

    def update_rating(self, rating: int):
        self.rating_sum += int(rating)
        self.rating_count += 1
        self.avg_rating = round(self.rating_sum / self.rating_count, 2)
        self.save(
            update_fields=["rating_sum", "rating_count", "avg_rating", "updated_at"]
        )

class SavedAddress(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="saved_addresses",
    )
    label = models.CharField(max_length=50, help_text="e.g. Home, Work, Gym")
    address = models.TextField()
    latitude = models.DecimalField(max_digits=12, decimal_places=9, null=True, blank=True)
    longitude = models.DecimalField(max_digits=12, decimal_places=9, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.label}: {self.address[:30]} ({self.user.phone})"


class StaticContent(models.Model):
    """
    Store dynamic text for screens like 'About Us', 'Privacy Policy', 'Terms of Service'
    """
    key = models.SlugField(unique=True, help_text="e.g. 'about_us', 'privacy_policy'")
    title = models.CharField(max_length=200)
    content = models.TextField()
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class SocialAccount(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="social_accounts"
    )
    provider = models.CharField(
        max_length=20, help_text="e.g. 'google', 'apple', 'facebook'"
    )
    uid = models.CharField(max_length=255, unique=True, help_text="Social Provider ID")
    extra_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "provider")

    def __str__(self):
        return f"{self.user.username} - {self.provider}"
class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Wallet: {self.user.phone} - Bal: {self.balance}"


class DriverUser(User):
    class Meta:
        proxy = True


class RiderUser(User):
    class Meta:
        proxy = True
