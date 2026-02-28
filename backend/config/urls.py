# project/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),

    # API routes
    path("api/drivers/", include("apps.drivers.urls")),
    path("api/rides/", include("apps.rides.urls")),   # ✅ Correct prefix
    path("api/users/", include("apps.users.urls")),
    path("api/payments/", include("apps.payments.urls")),
    path("api/supports/", include("apps.supports.urls")),
    path("api/tracking/", include("apps.tracking.urls")),
    path("api/notifications/", include("apps.notifications.urls")),
    path("api/admin/", include("apps.admin_dashboard.urls")),
    path("api/offers/", include("apps.offers.urls")),
    path("api/driver-incentives/", include("apps.driver_incentives.urls")),
]

# ============================
# ERROR HANDLERS
# ============================
handler400 = "django.views.defaults.bad_request"
handler403 = "django.views.defaults.permission_denied"
handler404 = "django.views.defaults.page_not_found"
handler500 = "django.views.defaults.server_error"

# ============================
# STATIC FILES (DEV ONLY)
# ============================
if settings.DEBUG:
    urlpatterns += static(
        settings.STATIC_URL,
        document_root=settings.STATIC_ROOT
    )
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )
