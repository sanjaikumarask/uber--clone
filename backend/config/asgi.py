import os

import django
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

import apps.admin_dashboard.routing
import apps.driver_incentives.routing
import apps.rides.routing
import apps.tracking.routing  # 🔥 ADD THIS
from apps.rides.middleware import JwtAuthMiddleware

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": JwtAuthMiddleware(
            URLRouter(
                apps.rides.routing.websocket_urlpatterns
                + apps.admin_dashboard.routing.websocket_urlpatterns
                + apps.driver_incentives.routing.websocket_urlpatterns
                + apps.tracking.routing.websocket_urlpatterns  # 🔥 ADD THIS
            )
        ),
    }
)
