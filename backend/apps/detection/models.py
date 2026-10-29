import os
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


def detection_photo_path(instance, filename):
    """Store each photo under a random name (detections/2026/10/<random>.jpg) so its web address cannot be guessed."""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in (".jpg", ".jpeg", ".png", ".webp"):
        ext = ".jpg"
    return f"detections/{timezone.now():%Y/%m}/{uuid.uuid4().hex}{ext}"


class Detection(models.Model):
    """One uploaded leaf photo and what the YOLO model found in it."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="detections")
    crop = models.CharField(max_length=20, default="maize")
    image = models.ImageField(upload_to=detection_photo_path)
    image_width = models.PositiveIntegerField(null=True, blank=True)
    image_height = models.PositiveIntegerField(null=True, blank=True)
    # "disease" (a disease was found), "healthy" (the model recognised a healthy leaf), "none" (nothing detected)
    # or "other" (Gemini says it is not a maize/cassava leaf, so the app gives no verdict; crop is then "other")
    status = models.CharField(max_length=10, default="none")
    top_label = models.CharField(max_length=100, blank=True)
    top_confidence = models.FloatField(null=True, blank=True)
    # list of {"label": str, "confidence": float, "bbox": [x1, y1, x2, y2]}
    results = models.JSONField(default=list, blank=True)
    advice = models.TextField(blank=True)
    # Gemini's second opinion on this photo (see advisor.verify_detection); {} until it has been asked.
    verification = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.top_label or 'no detection'} ({self.created_at:%Y-%m-%d})"
