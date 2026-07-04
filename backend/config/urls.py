from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from config.views import health

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/health/", health, name="health"),
    path("api/v1/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.audit.urls")),
    path("api/v1/", include("apps.basedata.urls")),
    path("api/v1/", include("apps.enrollment.urls")),
    path("api/v1/", include("apps.matching.urls")),
    path("api/v1/", include("apps.investigation.urls")),
    path("api/v1/", include("apps.pis.urls")),
    path("api/v1/", include("apps.watchlist.urls")),
    path("api/v1/", include("apps.registration.urls")),
    path("api/v1/", include("apps.appointments.urls")),
    path("api/v1/", include("apps.payments.urls")),
    path("api/v1/", include("apps.clearance.urls")),
    path("api/v1/", include("apps.verification.urls")),
    path("api/v1/", include("apps.notifications.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
