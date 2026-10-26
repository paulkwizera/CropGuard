"""
Quick check that a detector works on a real photo, without starting the website:

    python manage.py try_detector path/to/leaf.jpg                 # what the website does: auto-detect the crop
    python manage.py try_detector path/to/leaf.jpg --crop cassava  # force one crop's model

With auto (the default) it shows how sure EACH crop's model is and which crop wins, so you can see why a
photo was read as maize or cassava. With --crop it prints what that one model finds at several confidence
thresholds, so you can see whether nothing is detected because the threshold (YOLO_CONF in .env) is too strict.
"""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.detection import crops
from apps.detection.services import yolo


class Command(BaseCommand):
    help = "Run a crop detector on one image and print the detections at several confidence thresholds."

    def add_arguments(self, parser):
        parser.add_argument("image")
        parser.add_argument("--crop", default=crops.AUTO, choices=crops.choices())

    def handle(self, image, crop, **options):
        if crop == crops.AUTO:
            return self.handle_auto(image)
        if not crops.is_available(crop):
            raise CommandError(f"No model file for {crop}: expected {crops.model_path(crop)}")
        self.stdout.write(f"Model: {crops.model_path(crop)}   image size: {settings.YOLO_IMGSZ}   current YOLO_CONF: {settings.YOLO_CONF}")
        for conf in (0.1, 0.25, 0.4, 0.5, 0.6, 0.8):
            out = yolo.predict(image, crop, conf=conf)
            found = ", ".join(f"{r['label']} {r['confidence']:.0%}" for r in out["results"]) or "nothing"
            self.stdout.write(f"  conf >= {conf:<4}: {found}")

    def handle_auto(self, image):
        available = [c for c in crops.crop_ids() if crops.is_available(c)]
        if not available:
            raise CommandError("No crop model files found in ml/weights.")
        self.stdout.write(f"Auto-detect over: {', '.join(available)}   report threshold (YOLO_CONF): {settings.YOLO_CONF}")
        for crop in available:
            found = yolo.predict(image, crop, conf=yolo.AUTO_FLOOR)["results"]
            top = ", ".join(f"{r['label']} {r['confidence']:.0%}" for r in found[:3]) or "nothing"
            self.stdout.write(f"  {crop:<8} model sees: {top}")
        out = yolo.predict_auto(image)
        shown = ", ".join(f"{r['label']} {r['confidence']:.0%}" for r in out["results"]) or "nothing above the threshold"
        self.stdout.write(self.style.SUCCESS(f"-> crop: {out['crop']}   reported: {shown}"))
