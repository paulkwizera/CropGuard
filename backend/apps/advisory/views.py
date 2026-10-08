from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import AdvisoryRequestSerializer, WeatherQuerySerializer
from .services import advisor, weather


class WeatherView(APIView):
    """GET /api/advisory/weather/?city=Musanze -> next-24h forecast summary."""

    def get(self, request):
        query = WeatherQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        city = query.validated_data["city"]
        summary = weather.summarize_forecast(weather.fetch_forecast(city))
        return Response({"city": city, **summary})


class AdvisoryView(APIView):
    """POST /api/advisory/ {city, language} -> forecast + AI farming advice."""

    def post(self, request):
        body = AdvisoryRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        city, language = body.validated_data["city"], body.validated_data["language"]
        summary = weather.summarize_forecast(weather.fetch_forecast(city))
        text = advisor.weather_advisory(city, summary, language)
        return Response({"city": city, "language": language, "weather": summary, "advisory": text})
