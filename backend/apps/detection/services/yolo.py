"""
YOLOv8 inference wrapper (one model per crop).

Each model is loaded once, on first use, so Django starts fast and `manage.py check/test`
work even if ultralytics/torch is not installed.
"""
from functools import lru_cache

from django.conf import settings

from apps.core.exceptions import ServiceUnavailable

from .. import crops


@lru_cache(maxsize=4)
def _load_model(path: str):
    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise ServiceUnavailable("ultralytics is not installed (pip install -r requirements.txt)") from exc
    return YOLO(path)


def get_model(crop: str):
    if not crops.is_available(crop):
        name = settings.CROP_MODELS.get(crop, {}).get("name", crop)
        raise ServiceUnavailable(f"The {name.lower()} detector is not available yet.")
    return _load_model(str(crops.model_path(crop)))


def predict(image_path, crop: str = "maize", conf: float | None = None) -> dict:
    """Run detection on one image file.

    Returns {"width", "height", "results": [{"code", "label", "healthy", "confidence", "bbox"}...]}
    sorted by confidence (highest first). `results` is empty when nothing passes the threshold.
    """
    model = get_model(crop)
    result = model.predict(
        source=str(image_path), conf=conf if conf is not None else settings.YOLO_CONF,
        imgsz=settings.YOLO_IMGSZ, verbose=False,
    )[0]
    height, width = result.orig_shape
    found = []
    for box in result.boxes:
        code = str(result.names[int(box.cls[0])])
        found.append({
            "code": code,
            "label": crops.display_label(crop, code),
            "healthy": crops.is_healthy(crop, code),
            "confidence": round(float(box.conf[0]), 4),
            "bbox": [round(float(v), 1) for v in box.xyxy[0].tolist()],
        })
    found.sort(key=lambda item: item["confidence"], reverse=True)
    return {"width": int(width), "height": int(height), "results": found}
