"""OpenWeatherMap 5-day / 3-hour forecast (ported from the original weather_advisor.py)."""
import requests
from django.conf import settings

from apps.core.exceptions import ExternalServiceError, PlaceNotFound

from .districts import coords_for

FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"


def _location_params(city: str) -> dict:
    """Rwandan districts go by coordinates (OpenWeather doesn't know most of them);
    anything else (a town the farmer typed) falls back to a name search in Rwanda."""
    coords = coords_for(city)
    if coords:
        return {"lat": coords[0], "lon": coords[1]}
    return {"q": f"{city},RW"}


def fetch_forecast(city: str) -> dict:
    if not settings.OPENWEATHER_API_KEY:
        raise ExternalServiceError("OPENWEATHER_API_KEY is not configured.")
    try:
        response = requests.get(
            FORECAST_URL,
            params={**_location_params(city), "appid": settings.OPENWEATHER_API_KEY, "units": "metric"},
            timeout=5,
        )
    except requests.RequestException as exc:
        raise ExternalServiceError("Weather service is unreachable.") from exc
    if response.status_code == 404:
        raise PlaceNotFound(f"'{city}' was not found. Try your district or the nearest big town.")
    if response.status_code != 200:
        raise ExternalServiceError("Weather service returned an error.")
    return response.json()


def summarize_forecast(raw: dict, slots: int = 8) -> dict:
    """Reduce the raw API payload to the next `slots` x 3h readings (8 = next 24 hours)."""
    readings = [
        {
            "datetime": item["dt_txt"],
            "temp_c": item["main"]["temp"],
            "humidity": item["main"]["humidity"],
            "description": item["weather"][0]["description"],
            "wind_m_s": item["wind"]["speed"],
            "rain_mm": item.get("rain", {}).get("3h", 0),
        }
        for item in raw["list"][:slots]
    ]
    return {
        "readings": readings,
        "total_rain_mm": round(sum(r["rain_mm"] for r in readings), 1),
        "avg_temp_c": round(sum(r["temp_c"] for r in readings) / len(readings), 1) if readings else None,
    }
