from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("apps.core.urls")),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/detections/", include("apps.detection.urls")),
    path("api/advisory/", include("apps.advisory.urls")),
    path("api/assistant/", include("apps.assistant.urls")),
]

# Uploaded leaf photos. Served by Django itself (fine for a small app); the file names are random, so they cannot be guessed.
urlpatterns += [re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT})]
