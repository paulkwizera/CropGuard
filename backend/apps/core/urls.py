from django.urls import path

from .views import ai_status, health

urlpatterns = [
    path("health/", health, name="health"),
    path("health/ai/", ai_status, name="health-ai"),
]
