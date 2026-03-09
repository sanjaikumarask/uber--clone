import os
from datetime import timedelta
from pathlib import Path

# ============================================================
# BASE
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("SECRET_KEY")

DEBUG = os.getenv("DEBUG", "0") == "1"

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
    "django_prometheus",  # 🔥 APM Metrics
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
    "apps.common",
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
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
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
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "1000/day",  # Prevent bruteforce from public endpoints
        "user": "50000/day",  # Higher limit for polling dashboards
    },
    "EXCEPTION_HANDLER": "rest_framework.views.exception_handler",
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
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "apps.common.resilience.TracingMiddleware",  # 🔥 1. Trace Entry
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.common.rate_limit.RateLimitMiddleware",  # 🔥 2. Protect Endpoints
    "django.contrib.messages.middleware.MessageMiddleware",
    "apps.common.idempotency.IdempotencyMiddleware",  # 🔥 3. Dedup Side-effects
    "django_prometheus.middleware.PrometheusAfterMiddleware",
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

import sys

IS_TESTING = "pytest" in sys.modules or "test" in sys.argv

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "uber"),
        "USER": os.getenv("POSTGRES_USER", "uber"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", "uber" if (os.getenv("DEBUG", "0") == "1") else ""),
        "HOST": os.getenv("POSTGRES_HOST", "postgres"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": (
            0 if IS_TESTING else 60
        ),  # 🚀 POOLING: Disable for tests to avoid locking
        "OPTIONS": {
            "connect_timeout": 5,
        },
    }
}

# ============================================================
# CACHES (Redis Pooling)
# ============================================================

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {
                "max_connections": 100,
                "retry_on_timeout": True,
            },
            "SOCKET_CONNECT_TIMEOUT": 5,
            "SOCKET_TIMEOUT": 5,
        },
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
# CELERY (High Load Strategy)
# ============================================================

from celery.schedules import crontab
from kombu import Exchange, Queue

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "django-db")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_TASK_ACKS_LATE = True

if IS_TESTING:
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_WORKER_SEND_TASK_EVENTS = True  # 🔥 Required for Flower
CELERY_TASK_SEND_SENT_EVENT = True  # 🔥 Required for Flower

# ── Queue Definitions ──
CELERY_QUEUES = (
    Queue("high", Exchange("high"), routing_key="high"),
    Queue("medium", Exchange("medium"), routing_key="medium"),
    Queue("low", Exchange("low"), routing_key="low"),
)

CELERY_TASK_DEFAULT_QUEUE = "medium"
CELERY_TASK_DEFAULT_EXCHANGE = "medium"
CELERY_TASK_DEFAULT_ROUTING_KEY = "medium"

# ── Task Routing (Obsessively Prioritized) ──
CELERY_TASK_ROUTES = {
    # HIGH PRIORITY (Blocking UX)
    "apps.payments.tasks.process_driver_payout": {"queue": "high"},
    "apps.payments.tasks.execute_driver_payout": {"queue": "high"},
    "apps.rides.tasks.driver_accept_timeout": {"queue": "high"},
    # MEDIUM PRIORITY (Revenue/Flow)
    "apps.rides.services.matching.*": {"queue": "medium"},
    "apps.rides.tasks.retry_matching*": {"queue": "medium"},
    "apps.payments.tasks.reconcile*": {"queue": "medium"},
    # LOW PRIORITY (Non-Blocking)
    "apps.drivers.tasks.*": {"queue": "low"},
    "apps.notifications.tasks.*": {"queue": "low"},
}

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
    "reconcile-processing-payouts": {
        "task": "apps.payments.tasks.reconcile_processing_payouts",
        "schedule": 900.0,  # Every 15 mins
    },
    # ─── 4. PERIODIC RECONCILIATION & CHAOS ──────────────────
    "reconcile_all_rides_daily": {
        "task": "apps.payments.tasks.audit_platform_ledger",
        "schedule": crontab(hour=3, minute=0),  # 3 AM
    },
    "chaos_simulation_hourly": {
        "task": "apps.common.tasks.run_chaos_simulation",
        "schedule": crontab(minute=0),  # Every hour
    },
    "update_system_health_30s": {
        "task": "apps.common.tasks.update_system_health",
        "schedule": 30.0,  # Every 30 seconds
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
    "prune-ghost-drivers": {
        "task": "apps.drivers.tasks.prune_ghost_driver_sessions",
        "schedule": 120.0,  # Every 2 minutes
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
            "expiry": 10,  # Drop stale location pings quickly
        },
    },
}

# ============================================================
# REDIS / KAFKA
# ============================================================

KAFKA_BOOTSTRAP_SERVERS = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS",
    "kafka:9092",
)

# ============================================================
# DOMAIN CONFIG
# ============================================================

RIDE_DRIVER_ACCEPT_TIMEOUT = 30  # seconds

# ============================================================
# CORS  (all origins use HTTPS — no plaintext http:// references)
# ============================================================

HTTPS_PROTOCOL = "https://"

# Localhost origins use HTTPS so that browsers with strict mixed-content
# policies (and local reverse-proxies / mkcert) work correctly.
# Override via the CORS_ALLOWED_ORIGINS env-var in any environment.
DEFAULT_LOCAL_ORIGINS = [
    f"{HTTPS_PROTOCOL}localhost:5173",
    f"{HTTPS_PROTOCOL}localhost:5174",
]

CORS_ALLOWED_ORIGINS = (
    os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")
    if os.getenv("CORS_ALLOWED_ORIGINS")
    else DEFAULT_LOCAL_ORIGINS
)

CSRF_TRUSTED_ORIGINS = (
    os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",")
    if os.getenv("CSRF_TRUSTED_ORIGINS")
    else DEFAULT_LOCAL_ORIGINS
)

# All origins are already https:// — no runtime replacement needed.


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

DEFAULT_FROM_EMAIL = os.getenv(
    "DEFAULT_FROM_EMAIL", os.getenv("EMAIL_HOST_USER", "noreply@uberclone.com")
)

TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_FROM_NUMBER = os.environ.get("TWILIO_FROM_NUMBER")


RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")
RAZORPAY_PAYOUT_WEBHOOK_SECRET = os.getenv("RAZORPAY_PAYOUT_WEBHOOK_SECRET", "")

RAZORPAY_ACCOUNT_NUMBER = os.getenv(
    "RAZORPAY_ACCOUNT_NUMBER", "2323230000000000"
)  # Dummy Default

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
        "json": {
            "()": "apps.common.logging.JSONFormatter",
        },
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "json" if not DEBUG else "verbose",
        },
        "redis": {
            "level": "INFO",
            "class": "apps.common.logging.RedisLogHandler",
            "formatter": "json",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console", "redis"],
            "level": "INFO",
            "propagate": True,
        },
        "apps": {
            "handlers": ["console", "redis"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# Add basic sentry integration safely (if DSN exists in env)
SENTRY_DSN = os.getenv("SENTRY_DSN")
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.redis import RedisIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration(), RedisIntegration(), CeleryIntegration()],
        traces_sample_rate=1.0 if DEBUG else 0.1,  # 10% traces in prod
        send_default_pii=True,
    )
