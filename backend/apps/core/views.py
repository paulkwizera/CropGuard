from django.core.cache import cache
from django.db import connection
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from . import gemini


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


@api_view(["GET"])
@permission_classes([AllowAny])
def ai_status(request):
    """Is Gemini working? Open /api/health/ai/ in a browser: it makes one tiny real call and says what is wrong.

    The answer is kept for 60 seconds, so refreshing the page cannot use up quota. Nothing secret is shown
    (only the key's FORMAT and length, never the key itself).
    """
    report = cache.get("gemini-status")
    if report is None:
        report = gemini.diagnose()
        for row in report["checks"]:
            row.pop("error", None)   # Google's raw error text stays in the server log, not on a public page
        cache.set("gemini-status", report, 60)
    return Response(report)
