from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from apps.core import gemini
from apps.core.exceptions import ExternalServiceError


class SDKError(Exception):
    """Looks like google.genai.errors.APIError: it carries .code and .status."""

    def __init__(self, code, status, message=""):
        self.code, self.status = code, status
        super().__init__(f"{code} {status}. {message}")


def reply(text):
    return MagicMock(text=text)


@override_settings(GOOGLE_API_KEY=' "AQ.test-key" ', GEMINI_MODEL="m1", GEMINI_FALLBACK_MODELS="m2,m3", GEMINI_THINKING="low")
@patch("apps.core.gemini.time.sleep", lambda s: None)
@patch("google.genai.Client")
class GeminiTests(SimpleTestCase):
    def setUp(self):
        gemini._state.update(preferred=None, last=None)

    def calls(self, client):
        return client.return_value.models.generate_content

    def test_key_is_tidied_and_its_format_named(self, client):
        self.assertEqual(gemini.api_key(), "AQ.test-key")
        self.assertTrue(gemini.key_format().startswith("AQ."))

    def test_fast_settings_are_sent(self, client):
        self.calls(client).return_value = reply("hi")
        self.assertEqual(gemini.generate("x", json_output=True), "hi")
        config = self.calls(client).call_args.kwargs["config"]
        self.assertEqual(str(config.thinking_config.thinking_level.value), "LOW")
        self.assertEqual(config.response_mime_type, "application/json")

    def test_a_busy_model_is_retried_once(self, client):
        self.calls(client).side_effect = [SDKError(503, "UNAVAILABLE"), reply("ok")]
        self.assertEqual(gemini.generate("x"), "ok")
        self.assertEqual([c.kwargs["model"] for c in self.calls(client).call_args_list], ["m1", "m1"])

    def test_a_rejected_key_stops_at_once_and_says_so(self, client):
        self.calls(client).side_effect = SDKError(401, "UNAUTHENTICATED", "ACCESS_TOKEN_TYPE_UNSUPPORTED")
        with self.assertRaises(ExternalServiceError) as ctx:
            gemini.generate("x")
        self.assertEqual(ctx.exception.get_codes(), "gemini_auth")
        self.assertEqual(self.calls(client).call_count, 1)

    def test_400_api_key_not_valid_counts_as_a_key_problem(self, client):
        self.calls(client).side_effect = SDKError(400, "INVALID_ARGUMENT", "API key not valid. Please pass a valid API key.")
        with self.assertRaises(ExternalServiceError) as ctx:
            gemini.generate("x")
        self.assertEqual(ctx.exception.get_codes(), "gemini_auth")

    def test_missing_or_over_quota_model_falls_back_and_is_remembered(self, client):
        self.calls(client).side_effect = [SDKError(404, "NOT_FOUND", "model not found"), SDKError(429, "RESOURCE_EXHAUSTED"), reply("ok")]
        self.assertEqual(gemini.generate("x"), "ok")
        self.assertEqual(gemini.models()[0], "m3")

    def test_a_model_that_refuses_thinking_level_is_retried_plain(self, client):
        self.calls(client).side_effect = [SDKError(400, "INVALID_ARGUMENT", "thinking_level unsupported"), reply("ok")]
        self.assertEqual(gemini.generate("x"), "ok")
        first, second = [c.kwargs["config"] for c in self.calls(client).call_args_list]
        self.assertIsNotNone(first.thinking_config)
        self.assertIsNone(second.thinking_config)

    def test_unknown_failure_becomes_a_clean_error_after_trying_every_model(self, client):
        self.calls(client).side_effect = RuntimeError("boom")
        with self.assertRaises(ExternalServiceError):
            gemini.generate("x")
        self.assertEqual(self.calls(client).call_count, 3)

    def test_empty_answer_is_reported(self, client):
        self.calls(client).return_value = reply(None)
        with self.assertRaises(ExternalServiceError) as ctx:
            gemini.generate("x")
        self.assertEqual(ctx.exception.get_codes(), "gemini_empty")

    @override_settings(GOOGLE_API_KEY="")
    def test_missing_key_is_reported(self, client):
        with self.assertRaises(ExternalServiceError) as ctx:
            gemini.generate("x")
        self.assertEqual(ctx.exception.get_codes(), "gemini_not_configured")

    def test_diagnose_explains_a_bad_key_without_revealing_it(self, client):
        self.calls(client).side_effect = SDKError(401, "UNAUTHENTICATED", "ACCESS_TOKEN_TYPE_UNSUPPORTED")
        report = gemini.diagnose()
        self.assertFalse(report["ok"])
        self.assertEqual(report["checks"][0]["kind"], "auth")
        self.assertNotIn("test-key", str(report))
