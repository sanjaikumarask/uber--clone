from pathlib import Path
from datetime import timedelta
import os

# ============================================================
# BASE
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "dev-secret-key-change-this-to-at-least-32-characters-long"
)

DEBUG = os.getenv("DEBUG", "1") == "1"

ALLOWED_HOSTS = ["*"] if DEBUG else os.getenv("ALLOWED_HOSTS", "").split(",")

# ============================================================
# APPLICATIONS
# ============================================================

INSTALLED_APPS = [
    "corsheaders",

    # ---- Custom apps FIRST (CRITICAL) ----
    "apps.users",

    # ---- Django core ----
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # ---- Third-party ----
    "rest_framework",
    "channels",
    "django_celery_results",
    "rest_framework_simplejwt.token_blacklist",

    # ---- Domain apps ----
    "apps.drivers",
    "apps.rides",
    "apps.payments",
    "apps.tracking",
    "apps.supports",
    "apps.notifications",
    "apps.admin_dashboard",
    "apps.offers",
    "apps.driver_incentives",


]

# ============================================================
# AUTH
# ============================================================

AUTH_USER_MODEL = "users.User"

AUTHENTICATION_BACKENDS = [
    "apps.users.backends.PhoneBackend",
    "django.contrib.auth.backends.ModelBackend",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ============================================================
# REST FRAMEWORK / JWT
# ============================================================

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",  # ✅ REQUIRED
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle"
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/day",     # Prevent bruteforce from public endpoints
        "user": "1000/day"     # Allow normal usage but prevent spamming
    },
    "EXCEPTION_HANDLER": "rest_framework.views.exception_handler"
}


SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=12),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# ============================================================
# MIDDLEWARE
# ============================================================

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "apps.rides.idempotency.IdempotencyMiddleware",  # 🔥 NEW: Idempotent Mutations
]

# ============================================================
# URL / TEMPLATES
# ============================================================

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ============================================================
# DATABASE
# ============================================================

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "uber"),
        "USER": os.getenv("POSTGRES_USER", "uber"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", "uber"),
        "HOST": os.getenv("POSTGRES_HOST", "postgres"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
    }
}

# ============================================================
# I18N
# ============================================================

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ============================================================
# STATIC
# ============================================================

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"


# ============================================================
# CELERY
# ============================================================

from celery.schedules import crontab

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "django-db")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1

CELERY_BEAT_SCHEDULE = {
    "weekly-driver-payouts": {
        "task": "apps.payments.tasks.trigger_scheduled_payouts",
        "schedule": crontab(day_of_week=1, hour=3, minute=0),  # Mondays @ 3 AM
    },
    "retry-ride-matching": {
        "task": "apps.rides.tasks.retry_matching_for_searching_rides",
        "schedule": 15.0,  # Run every 15 seconds
    },
    "auto-resolve-stuck-rides": {
        "task": "apps.rides.tasks.auto_resolve_stuck_rides",
        "schedule": 600.0,  # Run every 10 minutes
    },
    "reconcile-pending-payments": {
        "task": "apps.payments.tasks.reconcile_pending_payments",
        "schedule": 900.0,  # Run every 15 minutes
    },
    "retry-failed-payouts": {
        "task": "apps.payments.tasks.retry_failed_payouts",
        "schedule": 900.0,
    },
    "audit-platform-ledger": {
        "task": "apps.payments.tasks.audit_platform_ledger",
        "schedule": 86400.0,  # Run daily
    },

    # ── Driver Management ───────────────────────────────────────────
    "recalculate-driver-scores": {
        "task": "apps.drivers.tasks.recalculate_all_driver_scores",
        "schedule": crontab(minute=0, hour="*/6"),  # Every 6 hours
    },
    "reset-weekly-driver-stats": {
        "task": "apps.drivers.tasks.reset_weekly_driver_stats",
        "schedule": crontab(day_of_week=1, hour=0, minute=0),  # Monday midnight
    },
    "lift-expired-suspensions": {
        "task": "apps.drivers.tasks.lift_expired_suspensions",
        "schedule": 300.0,  # Every 5 minutes
    },
    "driver-feedback-nudges": {
        "task": "apps.drivers.tasks.send_driver_feedback_nudges",
        "schedule": crontab(hour=10, minute=0),  # Daily at 10 AM
    },
}


# ============================================================
# CHANNELS / ASGI
# ============================================================

ASGI_APPLICATION = "config.asgi.application"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("redis", 6379)],
            "capacity": 1500,  # Handle 100+ drivers at once
            "expiry": 10,      # Drop stale location pings quickly
        },
    },
}

# ============================================================
# REDIS / KAFKA
# ============================================================

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

KAFKA_BOOTSTRAP_SERVERS = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS",
    "kafka:9092",
)

# ============================================================
# DOMAIN CONFIG
# ============================================================

RIDE_DRIVER_ACCEPT_TIMEOUT = 30  # seconds

# ============================================================
# CORS
# ============================================================

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://192.169.1.137:8000",
    "http://192.169.1.137:19000",
    "http://192.169.1.137:19001",
    "http://192.169.1.137",
    "http://10.247.72.202:8000",
    "http://10.247.72.202:19000",
    "http://10.247.72.202:19001",
    "http://10.247.72.202:8081",
    "http://10.247.72.202",
]


CSRF_TRUSTED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://192.169.1.137:8000",
    "http://192.169.1.137",
    "http://10.247.72.202:8000",
    "http://10.247.72.202",
]

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]

CORS_ALLOW_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]

# ============================================================
# EMAIL / SMS
# ============================================================

if os.getenv("EMAIL_HOST_USER"):
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
    EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
    EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "1") == "1"
    EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
    EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", os.getenv("EMAIL_HOST_USER", "noreply@uberclone.com"))

TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_FROM_NUMBER = os.environ.get("TWILIO_FROM_NUMBER")



RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")
RAZORPAY_PAYOUT_WEBHOOK_SECRET = os.getenv("RAZORPAY_PAYOUT_WEBHOOK_SECRET", "")

RAZORPAY_ACCOUNT_NUMBER = os.getenv("RAZORPAY_ACCOUNT_NUMBER", "2323230000000000") # Dummy Default

PLATFORM_USER_ID = 1 


# ============================================================
# SECURITY / DEFAULTS
# ============================================================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")


# ============================================================
# GOOGLE MAPS
# ============================================================

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

if not GOOGLE_MAPS_API_KEY:
    raise RuntimeError("GOOGLE_MAPS_API_KEY is not set")


# ============================================================
# LOGGING & MONITORING
# ============================================================

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": True,
        },
        "apps": {  # Catch all custom app loggers automatically
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# Add basic sentry integration safely (if DSN exists in env)
SENTRY_DSN = os.getenv("SENTRY_DSN")
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.redis import RedisIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration
    
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration(), RedisIntegration(), CeleryIntegration()],
        traces_sample_rate=1.0 if DEBUG else 0.1,  # 10% traces in prod
        send_default_pii=True
    )

