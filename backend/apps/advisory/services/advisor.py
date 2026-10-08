"""Gemini-powered advice. The SDK is imported lazily so the app boots without it."""
from django.conf import settings

from apps.core.exceptions import ExternalServiceError

LANGUAGE_NAMES = {"rw": "Kinyarwanda", "en": "English", "fr": "French"}


def _generate(prompt: str) -> str:
    if not settings.GOOGLE_API_KEY:
        raise ExternalServiceError("GOOGLE_API_KEY is not configured.")
    try:
        from google import genai

        client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        response = client.models.generate_content(model=settings.GEMINI_MODEL, contents=prompt)
        return (response.text or "").strip()
    except Exception as exc:  # SDK raises many types; surface one clean error
        raise ExternalServiceError("The AI advisor failed to respond.") from exc


def weather_advisory(city: str, summary: dict, language: str = "rw") -> str:
    prompt = f"""
You are an expert agricultural advisor assisting smallholder maize farmers in Rwanda.

Location: {city}, Rwanda
Forecast for the next 24 hours (3-hour steps): {summary['readings']}
Total expected rain: {summary['total_rain_mm']} mm

Instructions:
1. Summarize the weather simply.
2. Say clearly whether the farmer should irrigate, spray pesticides, harvest early, or protect soil from erosion.
3. Write the entire answer in {LANGUAGE_NAMES.get(language, 'English')}. Keep it encouraging, practical and short.
"""
    return _generate(prompt)


def disease_advice(disease: str, language: str = "rw") -> str:
    prompt = f"""
You are an expert agronomist helping smallholder maize farmers in Rwanda.
A detection model found this maize problem: "{disease}".

Explain in simple words: what it is, how to confirm it in the field, how to treat it with
affordable and locally available options, and how to stop it spreading next season.
Write the entire answer in {LANGUAGE_NAMES.get(language, 'English')}. Keep it under 200 words.
"""
    return _generate(prompt)
