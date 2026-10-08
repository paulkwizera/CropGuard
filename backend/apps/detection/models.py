from django.conf import settings
from django.db import models


class Detection(models.Model):
    """One uploaded leaf photo and what the YOLO model found in it."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="detections")
    image = models.ImageField(upload_to="detections/%Y/%m/")
    image_width = models.PositiveIntegerField(null=True, blank=True)
    image_height = models.PositiveIntegerField(null=True, blank=True)
    top_label = models.CharField(max_length=100, blank=True)
    top_confidence = models.FloatField(null=True, blank=True)
    # list of {"label": str, "confidence": float, "bbox": [x1, y1, x2, y2]}
    results = models.JSONField(default=list, blank=True)
    advice = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.top_label or 'no detection'} ({self.created_at:%Y-%m-%d})"
