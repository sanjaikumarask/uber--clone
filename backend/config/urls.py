from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),

    path("api/drivers/", include("apps.drivers.urls")),
    path("api/rides/", include("apps.rides.urls")),
    path("api/users/", include("apps.users.urls")),
    path("api/payments/", include("apps.payments.urls")),
    path("api/supports/", include("apps.supports.urls")),
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
