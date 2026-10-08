from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.advisory.services import advisor

from .models import Detection
from .serializers import AdviceRequestSerializer, DetectionSerializer
from .services import yolo


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

    def get_queryset(self):
        return Detection.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        detection = serializer.save(user=self.request.user)
        try:
            outcome = yolo.predict(detection.image.path)
        except Exception:
            detection.delete()  # don't keep an upload we could not analyse
            raise
        top = outcome["results"][0] if outcome["results"] else None
        detection.image_width = outcome["width"]
        detection.image_height = outcome["height"]
        detection.results = outcome["results"]
        detection.top_label = top["label"] if top else ""
        detection.top_confidence = top["confidence"] if top else None
        detection.save()

    @action(detail=True, methods=["post"])
    def advice(self, request, pk=None):
        """Ask the AI for treatment advice about the top disease of this detection."""
        detection = self.get_object()
        if not detection.top_label:
            return Response({"detail": "Nothing was detected in this image."}, status=status.HTTP_400_BAD_REQUEST)
        body = AdviceRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        detection.advice = advisor.disease_advice(detection.top_label, body.validated_data["language"])
        detection.save(update_fields=["advice"])
        return Response(self.get_serializer(detection).data)
