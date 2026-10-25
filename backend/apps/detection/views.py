from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from apps.advisory.services import advisor
from apps.core.exceptions import ServiceUnavailable

from . import crops
from .models import Detection
from .serializers import AdviceRequestSerializer, DetectionSerializer
from .services import yolo


def summarize(results: list[dict]) -> tuple[str, dict | None]:
    """Pick the headline of a check. A disease always wins over a 'healthy' region of the same photo."""
    diseases = [r for r in results if not r.get("healthy")]
    healthy = [r for r in results if r.get("healthy")]
    if diseases:
        return "disease", diseases[0]
    if healthy:
        return "healthy", healthy[0]
    return "none", None


class DetectionViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """A farmer only ever sees their own detections."""

    serializer_class = DetectionSerializer
    lookup_value_regex = "[0-9a-f]{24}"  # MongoDB ObjectId

    # Only the expensive actions are limited (a photo check runs the model, advice calls Gemini);
    # listing, viewing and deleting checks are not.
    throttle_classes = [ScopedRateThrottle]
    THROTTLE_SCOPES = {"create": "upload", "advice": "ai"}

    def get_throttles(self):
        self.throttle_scope = self.THROTTLE_SCOPES.get(self.action)  # None = no limit for this action
        return super().get_throttles()

    def get_queryset(self):
        return Detection.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        crop = serializer.validated_data.get("crop", "maize")
        if not crops.is_available(crop):  # e.g. cassava while its model is still being trained
            raise ServiceUnavailable(f"The {crop} detector is not available yet.")
        detection = serializer.save(user=self.request.user, crop=crop)
        try:
            outcome = yolo.predict(detection.image.path, crop)
        except Exception:
            detection.delete()  # don't keep an upload we could not analyse
            raise
        status_, top = summarize(outcome["results"])
        detection.status = status_
        detection.image_width = outcome["width"]
        detection.image_height = outcome["height"]
        detection.results = outcome["results"]
        detection.top_label = top["label"] if top else ""
        detection.top_confidence = top["confidence"] if top else None
        detection.save()

    @action(detail=False, methods=["get"])
    def crops(self, request):
        """Which crops can be checked right now (the cassava model is still being trained)."""
        return Response(crops.list_crops())

    @action(detail=True, methods=["post"])
    def advice(self, request, pk=None):
        """Ask the AI for treatment advice about the top disease of this detection."""
        detection = self.get_object()
        if detection.status != "disease":
            return Response({"detail": "Nothing was detected in this image."}, status=status.HTTP_400_BAD_REQUEST)
        body = AdviceRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        detection.advice = advisor.disease_advice(detection.top_label, body.validated_data["language"], crop=detection.crop)
        detection.save(update_fields=["advice"])
        return Response(self.get_serializer(detection).data)
