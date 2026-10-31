from django.urls import path

from .views import ChatStreamView, ChatView

urlpatterns = [
    path("chat/", ChatView.as_view(), name="assistant-chat"),
    path("chat/stream/", ChatStreamView.as_view(), name="assistant-chat-stream"),
]
