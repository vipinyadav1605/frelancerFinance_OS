from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("accounts.urls")),
    path("api/", include("clients.urls")),
    path("api/", include("invoicing.urls")),
    path("api/", include("expenses.urls")),
    path("api/", include("reports.urls")),
    path("api/", include("integrations.urls")),
    path("api/", include("notifications.urls")),
    path("api/", include("search.urls")),
    path("api/", include("billing.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
