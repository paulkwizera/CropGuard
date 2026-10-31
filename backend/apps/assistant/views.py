from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.core import streaming

from .serializers import ChatRequestSerializer
from .services import assistant


class ChatView(APIView):
    """POST /api/assistant/chat/ {messages, language, context?} -> {reply, language}"""

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "assistant"

    def post(self, request):
        body = ChatRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        data = body.validated_data
        reply = assistant.chat([dict(m) for m in data["messages"]], data["language"], dict(data.get("context") or {}))
        return Response({"reply": reply, "language": data["language"]})


class ChatStreamView(APIView):
    """POST /api/assistant/chat/stream/ (same body as chat/) -> a stream of events, see apps.core.streaming."""

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "assistant"

    def post(self, request):
        body = ChatRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        data = body.validated_data
        pieces = assistant.chat_stream([dict(m) for m in data["messages"]], data["language"], dict(data.get("context") or {}))
        return streaming.response(streaming.text_events(pieces))
