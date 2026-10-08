from rest_framework import status
from rest_framework.exceptions import APIException


class ServiceUnavailable(APIException):
    """A required local resource (e.g. the YOLO model file) is missing."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Service temporarily unavailable."
    default_code = "service_unavailable"


class ExternalServiceError(APIException):
    """A third-party API (weather, Gemini) failed or timed out."""

    status_code = status.HTTP_502_BAD_GATEWAY
    default_detail = "An upstream service failed."
    default_code = "external_service_error"
