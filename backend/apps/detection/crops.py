"""
Which crops CropGuard can check, where each model file lives, and what its classes are called.

Adding a crop (for example when the cassava model finishes training):
  1. put the trained weights at ml/weights/cassava.pt  (or set YOLO_MODEL_CASSAVA_PATH in .env)
  2. add its class codes to ml/labels.json under "cassava"
The crop switches from "coming soon" to "available" by itself as soon as the file exists.
"""
import json
from functools import lru_cache
from pathlib import Path

from django.conf import settings


def crop_ids() -> list[str]:
    return list(settings.CROP_MODELS)


def model_path(crop: str) -> Path:
    return Path(settings.CROP_MODELS[crop]["path"])


def is_available(crop: str) -> bool:
    return crop in settings.CROP_MODELS and model_path(crop).exists()


def list_crops() -> list[dict]:
    return [{"id": c, "name": cfg["name"], "available": is_available(c)} for c, cfg in settings.CROP_MODELS.items()]


@lru_cache(maxsize=1)
def _labels() -> dict:
    try:
        return json.loads(Path(settings.LABELS_PATH).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _entry(crop: str, code: str):
    return (_labels().get(crop) or {}).get(code)


def display_label(crop: str, code: str) -> str:
    """'MLB' -> 'Maize Leaf Blight'. Unknown codes are shown as they are."""
    entry = _entry(crop, code)
    if isinstance(entry, dict):
        return entry.get("name") or code
    return entry or code


def is_healthy(crop: str, code: str) -> bool:
    """True for a 'healthy leaf' class (the cassava model has one; the maize model does not)."""
    entry = _entry(crop, code)
    return bool(isinstance(entry, dict) and entry.get("healthy"))
