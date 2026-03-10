from django.apps import AppConfig


class DriverIncentivesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.driver_incentives"

    def ready(self):
        import apps.driver_incentives.signals  # noqa: F401
