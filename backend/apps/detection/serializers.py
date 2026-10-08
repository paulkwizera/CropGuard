from django.conf import settings
from rest_framework import serializers

from .models import Detection


class DetectionSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)

    class Meta:
        model = Detection
        fields = [
            "id", "image", "image_width", "image_height",
            "top_label", "top_confidence", "results", "advice", "created_at",
        ]
        read_only_fields = [f for f in fields if f != "image"]

    def validate_image(self, image):
        limit = settings.MAX_UPLOAD_MB * 1024 * 1024
        if image.size > limit:
            raise serializers.ValidationError(f"Image is larger than {settings.MAX_UPLOAD_MB} MB.")
        return image


class AdviceRequestSerializer(serializers.Serializer):
    language = serializers.ChoiceField(choices=["rw", "en", "fr"], default="rw")
