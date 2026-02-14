import os
import django

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

django.setup()

from apps.rides.middleware import JwtAuthMiddleware
import apps.rides.routing
import apps.admin_dashboard.routing  # ✅ ADD THIS

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": JwtAuthMiddleware(
            URLRouter(
                apps.rides.routing.websocket_urlpatterns
                + apps.admin_dashboard.routing.websocket_urlpatterns
            )
        ),
    }
)
