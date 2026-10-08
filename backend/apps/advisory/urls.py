from django.urls import path

from .views import AdvisoryView, WeatherView

urlpatterns = [
    path("weather/", WeatherView.as_view(), name="weather"),
    path("", AdvisoryView.as_view(), name="advisory"),
]
