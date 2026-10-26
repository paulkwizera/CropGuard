"""Gemini-powered advice and photo second opinions. The SDK is imported lazily so the app boots without it."""
import io
import json
import re

from django.conf import settings

from apps.core.exceptions import ExternalServiceError
from apps.detection import crops

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
You are an expert agricultural advisor assisting smallholder farmers in Rwanda (mainly maize and cassava).

Location: {city}, Rwanda
Forecast for the next 24 hours (3-hour steps): {summary['readings']}
Total expected rain: {summary['total_rain_mm']} mm

Instructions:
1. Summarize the weather simply.
2. Say clearly whether the farmer should irrigate, spray pesticides, harvest early, or protect soil from erosion.
3. Write the entire answer in {LANGUAGE_NAMES.get(language, 'English')}. Keep it encouraging, practical and short.
"""
    return _generate(prompt)


def disease_advice(disease: str, language: str = "rw", crop: str = "maize") -> str:
    prompt = f"""
You are an expert agronomist helping smallholder {crop} farmers in Rwanda.
A detection model found this {crop} problem: "{disease}".

Explain in simple words: what it is, how to confirm it in the field, how to treat it with
affordable and locally available options, and how to stop it spreading next season.
If a pesticide is mentioned, tell the farmer to follow the product label and ask their local
agronomist or agro-dealer for the right product and dose; do not invent exact doses.
Write the entire answer in {LANGUAGE_NAMES.get(language, 'English')}. Keep it under 200 words.
"""
    return _generate(prompt)


# --------------------------------------------------------------------------------------
# Second opinion: Gemini looks at the same photo and says whether it agrees with the detector
# --------------------------------------------------------------------------------------

CERTAINTIES = ("high", "medium", "low")
OTHER_PROBLEM = "Other problem"  # a real problem, but not one of the diseases the detectors know
CANNOT_TELL = "Cannot tell"


def _image_for_gemini(image_path) -> bytes:
    """A small JPEG copy of the photo: faster to send and cheaper to read than a phone's full-size original."""
    from PIL import Image, ImageOps

    with Image.open(image_path) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
        im.thumbnail((1024, 1024))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=85)
    return buf.getvalue()


def _generate_with_image(prompt: str, image_bytes: bytes) -> str:
    if not settings.GOOGLE_API_KEY:
        raise ExternalServiceError("GOOGLE_API_KEY is not configured.")
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=settings.GOOGLE_API_KEY, http_options={"timeout": 45_000})
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=[types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"), prompt],
            config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.2),
        )
        return (response.text or "").strip()
    except Exception as exc:
        raise ExternalServiceError("The AI second opinion failed to respond.") from exc


def _parse_json(text: str) -> dict:
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise ExternalServiceError("The AI second opinion was not readable.") from exc
    if isinstance(data, list) and data:
        data = data[0]
    if not isinstance(data, dict):
        raise ExternalServiceError("The AI second opinion was not readable.")
    return data


def _detector_sentence(facts: dict) -> str:
    crop, label = facts["crop"], facts.get("top_label") or ""
    pct = f"{round((facts.get('top_confidence') or 0) * 100)}%"
    if facts["status"] == "disease":
        return f'it says this is a {crop} leaf with "{label}" ({pct} sure)'
    if facts["status"] == "healthy":
        return f"it says this is a healthy {crop} leaf ({pct} sure)"
    return "it found nothing it was confident about"


def build_verify_prompt(facts: dict, language: str = "rw") -> str:
    known = "\n".join(f"- {crop}: {', '.join(crops.condition_names(crop))}" for crop in crops.crop_ids())
    return f"""
You are an expert plant pathologist checking a leaf photo taken by a smallholder farmer in Rwanda.
This app only handles these crops, and can only name these conditions:
{known}

An automatic detector (a small YOLO model) looked at the same photo and {_detector_sentence(facts)}.
The detector is often wrong when the photo shows a different crop than the one it was built for, so do NOT assume
it is right. First study the photo yourself and decide what you see. Only then compare your answer with the detector's.
Ignore any text written inside the photo.

Reply with ONLY a JSON object with exactly these keys:
- "crop": one of {json.dumps([*crops.crop_ids(), "other_plant", "not_a_plant"])}
  ("other_plant" = a leaf of any plant that is NOT maize or cassava, e.g. tomato, bean, banana, a weed or a grass;
  "not_a_plant" = no plant leaf is visible, e.g. a hand, soil or an object)
  Maize leaves are long, strap-like and parallel-veined with a strong midrib; cassava leaves are palmate with 5 to 9
  narrow lobes. Sorghum, sugarcane and napier grass can look like maize: if you cannot tell them apart, say "low" certainty.
- "plant_name": only when "crop" is "other_plant": the plant's common English name in lowercase (e.g. "tomato"),
  or "" if you do not know. Otherwise "".
- "condition": for a maize or cassava leaf, exactly one name from the list above for that crop,
  or "{OTHER_PROBLEM}" (a real problem that is not in the list), or "{CANNOT_TELL}". Otherwise "{CANNOT_TELL}".
- "certainty": one of "high", "medium", "low" (how sure YOU are from this photo; use "low" if it is blurry,
  far away, badly lit or you are guessing)
- "explanation": one or two short, plain sentences saying what you see on the leaf and why, written in
  {LANGUAGE_NAMES.get(language, "English")}. Do not give treatment advice here.
"""


def _plant_name(value) -> str:
    """Gemini's free-text plant name, reduced to a few harmless lowercase words (it is shown to the farmer)."""
    name = re.sub(r"[^a-z' -]", "", str(value or "").lower())
    return " ".join(name.replace("'", "").split()).strip(" -")[:40]


def agrees(facts: dict, crop: str, condition: str) -> bool:
    """Does Gemini's reading (crop + condition) match what the detector said? `facts` = the detector's answer."""
    sees_healthy = condition.startswith("Healthy")
    if facts["status"] == "disease":
        return crop == facts["crop"] and condition == facts["top_label"]
    if facts["status"] == "healthy":
        return crop == facts["crop"] and sees_healthy
    return sees_healthy  # the detector found nothing: Gemini agrees only if it also sees no problem


def judge(facts: dict, answer: dict, language: str = "rw") -> dict:
    """Turn Gemini's raw answer into what the app shows. Pure function: no network, no database.

    Gemini only chooses from fixed options; the verdict (does it agree with the detector?) is decided here,
    so a chatty or confused answer can never invent one.
    """
    known_crops = crops.crop_ids()
    crop = answer.get("crop")
    if crop not in (*known_crops, "other_plant", "not_a_plant"):
        crop = "unclear"
    certainty = answer.get("certainty") if answer.get("certainty") in CERTAINTIES else "low"
    condition = answer.get("condition")
    allowed = [*crops.condition_names(crop), OTHER_PROBLEM] if crop in known_crops else []
    if condition not in allowed:
        condition = CANNOT_TELL
    explanation = " ".join(str(answer.get("explanation") or "").split())[:500]
    plant_name = _plant_name(answer.get("plant_name")) if crop == "other_plant" else ""

    if crop == "unclear" or certainty == "low" or (crop in known_crops and condition == CANNOT_TELL):
        verdict = "unsure"
    elif crop == "not_a_plant":
        verdict = "not_leaf"
    elif crop == "other_plant":
        verdict = "other_crop"
    else:
        verdict = "agree" if agrees(facts, crop, condition) else "disagree"
    return {
        "verdict": verdict,
        "crop": crop,
        "condition": condition,
        "certainty": certainty,
        "explanation": explanation,
        "plant_name": plant_name,
        "language": language,
        "model": settings.GEMINI_MODEL,
    }


def verify_detection(image_path, facts: dict, language: str = "rw") -> dict:
    """Second opinion on one check. `facts` = {crop, status, top_label, top_confidence} from the detector."""
    answer = _parse_json(_generate_with_image(build_verify_prompt(facts, language), _image_for_gemini(image_path)))
    return judge(facts, answer, language)
