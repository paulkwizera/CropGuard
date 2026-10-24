"""
Quick check that a detector works on a real photo, without starting the website:

    python manage.py try_detector path/to/leaf.jpg
    python manage.py try_detector path/to/leaf.jpg --crop cassava

It prints what the model finds at several confidence thresholds, so you can see whether
nothing is detected because the threshold (YOLO_CONF in .env) is too strict.
"""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.detection import crops
from apps.detection.services import yolo


class Command(BaseCommand):
    help = "Run a crop detector on one image and print the detections at several confidence thresholds."

    def add_arguments(self, parser):
        parser.add_argument("image")
        parser.add_argument("--crop", default="maize", choices=crops.crop_ids())

    def handle(self, image, crop, **options):
        if not crops.is_available(crop):
            raise CommandError(f"No model file for {crop}: expected {crops.model_path(crop)}")
        self.stdout.write(f"Model: {crops.model_path(crop)}   image size: {settings.YOLO_IMGSZ}   current YOLO_CONF: {settings.YOLO_CONF}")
        for conf in (0.1, 0.25, 0.4, 0.5, 0.6, 0.8):
            out = yolo.predict(image, crop, conf=conf)
            found = ", ".join(f"{r['label']} {r['confidence']:.0%}" for r in out["results"]) or "nothing"
            self.stdout.write(f"  conf >= {conf:<4}: {found}")
