from unittest.mock import MagicMock, patch

from bson import ObjectId
from django.test import SimpleTestCase, override_settings
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.accounts.models import User
from apps.core.exceptions import ExternalServiceError

from .services import assistant
from .views import ChatStreamView, ChatView


class PromptTests(SimpleTestCase):
    def test_language_and_farmer_context_are_in_the_prompt(self):
        text = assistant.system_prompt("rw", {"district": "Musanze", "last_check": "Maize Streak Virus"})
        self.assertIn("Kinyarwanda", text)
        self.assertIn("Musanze", text)
        self.assertIn("Maize Streak Virus", text)

    def test_unknown_language_falls_back_to_english(self):
        self.assertIn("English", assistant.system_prompt("xx"))

    def test_history_is_trimmed_and_roles_are_mapped(self):
        msgs = [{"role": "user" if i % 2 == 0 else "assistant", "content": f"m{i}"} for i in range(30)]
        contents = assistant.build_contents(msgs)
        self.assertEqual(len(contents), assistant.MAX_HISTORY)
        self.assertEqual({c.role for c in contents}, {"user", "model"})
        self.assertEqual(contents[-1].parts[0].text, "m29")


@override_settings(GOOGLE_API_KEY="test-key")
class ChatServiceTests(SimpleTestCase):
    @patch("google.genai.Client")
    def test_returns_the_model_text(self, client):
        client.return_value.models.generate_content.return_value = MagicMock(text="  Plant early.  ")
        out = assistant.chat([{"role": "user", "content": "When do I plant maize?"}], "en")
        self.assertEqual(out, "Plant early.")
        kwargs = client.return_value.models.generate_content.call_args.kwargs
        self.assertIn("English", kwargs["config"].system_instruction)

    @patch("google.genai.Client")
    def test_sdk_failure_becomes_a_clean_error(self, client):
        client.return_value.models.generate_content.side_effect = RuntimeError("boom")
        with self.assertRaises(ExternalServiceError):
            assistant.chat([{"role": "user", "content": "hi"}], "en")

    @patch("google.genai.Client")
    def test_empty_answer_is_reported(self, client):
        client.return_value.models.generate_content.return_value = MagicMock(text=None)
        with self.assertRaises(ExternalServiceError):
            assistant.chat([{"role": "user", "content": "hi"}], "en")

    @override_settings(GOOGLE_API_KEY="")
    def test_missing_key_is_reported(self):
        with self.assertRaises(ExternalServiceError):
            assistant.chat([{"role": "user", "content": "hi"}], "en")


class ChatEndpointTests(SimpleTestCase):
    def call(self, payload, authed=True):
        request = APIRequestFactory().post("/api/assistant/chat/", payload, format="json")
        if authed:
            force_authenticate(request, user=User(id=ObjectId(), username="farmer"))
        return ChatView.as_view()(request)

    def test_requires_login(self):
        self.assertEqual(self.call({"messages": [{"role": "user", "content": "hi"}]}, authed=False).status_code, 401)

    def test_last_message_must_be_from_the_user(self):
        r = self.call({"messages": [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]})
        self.assertEqual(r.status_code, 400)

    def test_rejects_empty_and_oversized_messages(self):
        self.assertEqual(self.call({"messages": []}).status_code, 400)
        self.assertEqual(self.call({"messages": [{"role": "user", "content": "x" * 2001}]}).status_code, 400)

    @patch("apps.assistant.views.assistant.chat", return_value="Use certified seed.")
    def test_success(self, chat):
        r = self.call({"messages": [{"role": "user", "content": "How do I get more maize?"}], "language": "fr", "context": {"district": "Huye"}})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data, {"reply": "Use certified seed.", "language": "fr"})
        self.assertEqual(chat.call_args.args[1], "fr")
        self.assertEqual(chat.call_args.args[2], {"district": "Huye"})


def read_events(response):
    """The (name, data) pairs of a streamed answer, in order."""
    import json

    text = b"".join(response.streaming_content).decode()
    return [(b.split("\n")[0][7:], json.loads(b.split("\n")[1][6:])) for b in text.split("\n\n") if b.startswith("event:")]


@override_settings(GOOGLE_API_KEY="test-key")
class ChatStreamEndpointTests(SimpleTestCase):
    def call(self, payload, authed=True):
        request = APIRequestFactory().post("/api/assistant/chat/stream/", payload, format="json")
        if authed:
            force_authenticate(request, user=User(id=ObjectId(), username="farmer"))
        return ChatStreamView.as_view()(request)

    def test_requires_login_and_validates_before_streaming(self):
        ok = {"messages": [{"role": "user", "content": "hi"}]}
        self.assertEqual(self.call(ok, authed=False).status_code, 401)
        self.assertEqual(self.call({"messages": []}).status_code, 400)   # a normal JSON error, not a stream

    @patch("google.genai.Client")
    def test_the_answer_arrives_piece_by_piece_then_done(self, client):
        client.return_value.models.generate_content_stream.return_value = iter([MagicMock(text="Plant "), MagicMock(text="early.")])
        r = self.call({"messages": [{"role": "user", "content": "When do I plant?"}], "language": "en"})
        self.assertEqual(r.status_code, 200)
        self.assertIn("text/event-stream", r["Content-Type"])
        self.assertEqual(read_events(r), [("chunk", {"t": "Plant "}), ("chunk", {"t": "early."}), ("done", {"text": "Plant early."})])

    @patch("google.genai.Client")
    def test_a_failure_is_an_error_event_with_a_friendly_message(self, client):
        client.return_value.models.generate_content_stream.side_effect = RuntimeError("boom")
        events = read_events(self.call({"messages": [{"role": "user", "content": "hi"}], "language": "en"}))
        self.assertEqual(events[-1][0], "error")
        self.assertNotIn("boom", str(events))
