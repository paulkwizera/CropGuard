"""
YOLOv8 inference wrapper (one model per crop).

Each model is loaded once, on first use, so Django starts fast and `manage.py check/test`
work even if ultralytics/torch is not installed.
"""
import gc
import logging
import threading
from functools import lru_cache

from django.conf import settings

from apps.core.exceptions import ServiceUnavailable

from .. import crops

log = logging.getLogger("cropguard.yolo")


# Only ONE photo goes through PyTorch at a time. Each running inference needs tens of MB of working memory, so with
# 4 server threads and 4 farmers at once a 512 MB free instance runs out and Render restarts it. The CPU is the
# bottleneck anyway, so waiting in line is no slower. (Gemini calls are not behind this lock: they only wait on the network.)
_inference_lock = threading.Lock()
_load_lock = threading.Lock()   # two threads must never load the same model at once (that would double the memory)


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
    with _load_lock:
        return _load_model(str(crops.model_path(crop)))


# In auto mode every detector is run at this low floor so their confidences can be compared;
# only the winning crop's detections that also pass YOLO_CONF are reported.
AUTO_FLOOR = 0.10


def predict(image_path, crop: str, conf: float | None = None) -> dict:
    """Run one crop's detector on one image file. (To let CropGuard pick the crop, use predict_auto.)

    Returns {"width", "height", "results": [{"code", "label", "healthy", "confidence", "bbox"}...]}
    sorted by confidence (highest first). `results` is empty when nothing passes the threshold.
    """
    model = get_model(crop)
    with _inference_lock:
        result = model.predict(
            source=str(image_path), conf=conf if conf is not None else settings.YOLO_CONF,
            imgsz=settings.YOLO_IMGSZ, verbose=False,
        )[0]
        gc.collect()   # hand the working memory back before the next photo
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


def predict_auto(image_path, conf: float | None = None) -> dict:
    """Work out which crop the photo shows, then report that crop's findings.

    A detector only knows its own crop's classes, so shown a leaf from another crop it still has to answer
    with one of them (a cassava leaf comes out as "Maize Streak Virus"). So every available detector looks at
    the photo and we trust the one that is most sure of what it sees.

    Returns the same shape as predict() plus "crop" (the winner) and "scores" (each crop's top confidence).
    """
    threshold = conf if conf is not None else settings.YOLO_CONF
    available = [c for c in crops.crop_ids() if crops.is_available(c)]
    if not available:
        raise ServiceUnavailable("No crop detector is available yet.")
    outcomes = {c: predict(image_path, c, conf=min(AUTO_FLOOR, threshold)) for c in available}
    scores = {c: (o["results"][0]["confidence"] if o["results"] else 0.0) for c, o in outcomes.items()}
    best = max(available, key=lambda c: scores[c])
    chosen = dict(outcomes[best])
    chosen["results"] = [r for r in chosen["results"] if r["confidence"] >= threshold]
    chosen["crop"] = best
    chosen["scores"] = scores
    return chosen


def warm_up() -> None:
    """Load every detector and push one tiny blank image through it, in the background right after the server starts.

    Importing PyTorch and loading the models takes 20+ seconds on a free server. Doing it here means the first farmer's
    photo does not have to wait for it (it used to fail with a red error on the first try and work on the second).
    Never raises: a failure here only means the first photo pays the cost, as before.
    """
    try:
        import numpy as np

        for crop in crops.crop_ids():
            if not crops.is_available(crop):
                continue
            model = get_model(crop)
            with _inference_lock:
                model.predict(source=np.zeros((64, 64, 3), dtype=np.uint8), imgsz=settings.YOLO_IMGSZ, verbose=False)
                gc.collect()
        log.info("detectors warmed up")
    except Exception:
        log.warning("detector warm-up failed; the first photo will load them instead", exc_info=True)
