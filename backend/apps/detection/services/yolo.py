"""
YOLOv8 inference wrapper.

The model is loaded once, on first use, so Django starts fast and
`manage.py check/test` work even if ultralytics/torch is not installed.
"""
from functools import lru_cache

from django.conf import settings

from apps.core.exceptions import ServiceUnavailable


@lru_cache(maxsize=1)
def _load_model():
    path = settings.YOLO_MODEL_PATH
    if not path.exists():
        raise ServiceUnavailable(f"YOLO weights not found at {path}")
    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise ServiceUnavailable("ultralytics is not installed (pip install -r requirements.txt)") from exc
    return YOLO(str(path))


def predict(image_path) -> dict:
    """Run detection on one image file.

    Returns {"width": int, "height": int, "results": [{"label", "confidence", "bbox"}...]}
    sorted by confidence (highest first). `results` is empty when nothing passes YOLO_CONF.
    """
    model = _load_model()
    result = model.predict(
        source=str(image_path), conf=settings.YOLO_CONF, imgsz=settings.YOLO_IMGSZ, verbose=False
    )[0]
    height, width = result.orig_shape
    found = [
        {
            "label": result.names[int(box.cls[0])],
            "confidence": round(float(box.conf[0]), 4),
            "bbox": [round(float(v), 1) for v in box.xyxy[0].tolist()],
        }
        for box in result.boxes
    ]
    found.sort(key=lambda item: item["confidence"], reverse=True)
    return {"width": int(width), "height": int(height), "results": found}
