from django.db import connection
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    """Used by the frontend and CI to check the API and MongoDB are reachable."""
    try:
        connection.database.command("ping")
        mongo = "ok"
    except Exception as exc:  # noqa: BLE001 - we only report status here
        mongo = f"unreachable: {exc.__class__.__name__}"
    return Response({"status": "ok", "mongodb": mongo})
