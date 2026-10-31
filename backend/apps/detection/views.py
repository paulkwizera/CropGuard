from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from apps.advisory.services import advisor
from apps.core.exceptions import ServiceUnavailable

from . import crops
from .models import Detection
from .serializers import AdviceRequestSerializer, DetectionSerializer
from .services import decision, imaging, yolo
from .services.decision import summarize  # noqa: F401  (kept importable from here)


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
    THROTTLE_SCOPES = {"create": "upload", "advice": "ai", "verify": "verify"}

    def get_throttles(self):
        self.throttle_scope = self.THROTTLE_SCOPES.get(self.action)  # None = no limit for this action
        return super().get_throttles()

    def get_queryset(self):
        return Detection.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        crop = serializer.validated_data.get("crop", crops.AUTO)
        auto = crop == crops.AUTO
        if not auto and not crops.is_available(crop):  # e.g. a crop whose model file is missing
            raise ServiceUnavailable(f"The {crop} detector is not available yet.")
        # In auto mode the real crop is only known after the photo has been analysed.
        detection = serializer.save(user=self.request.user, crop="maize" if auto else crop)
        imaging.shrink_in_place(detection.image.path)   # smaller photo = far less memory on a free server
        try:
            if auto:
                outcome = yolo.predict_auto(detection.image.path)
                detection.crop = outcome["crop"]
            else:
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
        """Which crops can be checked right now (a crop is available once its model file exists)."""
        return Response(crops.list_crops())

    @action(detail=True, methods=["post"])
    def verify(self, request, pk=None):
        """Ask Gemini to look at the photo itself and say whether it agrees with the detector."""
        detection = self.get_object()
        body = AdviceRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        language = body.validated_data["language"]
        if not detection.verification:  # decided once per check: asking again returns the same final answer
            self.second_opinion(detection, language)
        return Response(self.get_serializer(detection).data)

    @staticmethod
    def second_opinion(detection, language):
        """Ask Gemini, then pick ONE final answer (see services/decision.py) and store it on the check."""
        detector = {
            "crop": detection.crop,
            "status": detection.status,
            "top_label": detection.top_label,
            "top_confidence": detection.top_confidence,
            "results": detection.results,
        }
        gemini = advisor.verify_detection(detection.image.path, detector, language)

        def rerun(crop):  # the right crop's detector, when Gemini says the photo shows another crop
            if not crops.is_available(crop):
                return None
            try:
                return yolo.predict(detection.image.path, crop)["results"]
            except Exception:
                return None

        outcome = decision.decide(detector, gemini, rerun)
        final = outcome["final"]
        detection.crop, detection.status = final["crop"], final["status"]
        detection.top_label, detection.top_confidence = final["top_label"], final["top_confidence"]
        detection.results = final["results"]
        detection.verification = {**gemini, "resolution": outcome["resolution"]}
        detection.save()

    @action(detail=True, methods=["post"])
    def advice(self, request, pk=None):
        """Ask the AI for treatment advice about the top disease of this detection."""
        detection = self.get_object()
        if detection.status != "disease":
            return Response({"detail": "Nothing was detected in this image."}, status=status.HTTP_400_BAD_REQUEST)
        body = AdviceRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        disease = detection.top_label
        seen = detection.verification or {}
        gemini_named_it = seen.get("condition") == advisor.OTHER_PROBLEM and (seen.get("resolution") or {}).get("winner") == "gemini"
        if gemini_named_it and seen.get("explanation"):  # the detector never knew this problem: give the AI what Gemini saw
            disease = f"{disease}. What a close look at the photo showed: {seen['explanation'][:300]}"
        detection.advice = advisor.disease_advice(disease, body.validated_data["language"], crop=detection.crop)
        detection.save(update_fields=["advice"])
        return Response(self.get_serializer(detection).data)
