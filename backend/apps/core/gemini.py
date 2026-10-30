"""
The ONE place CropGuard talks to Gemini (treatment advice, weather advice, the photo second opinion, Ask the AI).

Why this file exists: the same call used to be copy-pasted in three places, each one hiding every failure behind
"The AI advisor failed to respond." with nothing in the logs, so a wrong key, a wrong model name, a quota limit and a
slow network all looked identical. Now:

  * every failure is CLASSIFIED (bad key / quota / busy / model missing / ...), LOGGED (Render's Logs tab) and turned
    into a short, honest message the website can show;
  * a busy or slow model is retried once, then the next model in GEMINI_FALLBACK_MODELS is tried;
  * a rejected API key stops at once (no other model can fix a bad key);
  * calls are FAST: "low" thinking (Gemini 3 models think a lot by default), one warm HTTP client that is reused,
    and a total time budget so a farmer is never left waiting for minutes;
  * diagnose() tells you in seconds what is wrong (used by `manage.py check_gemini` and /api/health/ai/).

The SDK is imported lazily so Django boots (and tests run) without it.
"""
import logging
import threading
import time

from django.conf import settings

from .exceptions import ExternalServiceError

log = logging.getLogger("cropguard.gemini")

# What to tell the farmer / the developer for each kind of failure: (error code, message).
MESSAGES = {
    "not_configured": ("gemini_not_configured", "GOOGLE_API_KEY is not configured."),
    "auth": ("gemini_auth", "The AI service rejected its API key. The site owner must set a valid Gemini key."),
    "quota": ("gemini_quota", "The AI service has reached its usage limit. Please try again in a minute."),
    "busy": ("gemini_busy", "The AI service is busy right now. Please try again in a moment."),
    "timeout": ("gemini_timeout", "The AI service is too slow right now. Please try again in a moment."),
    "network": ("gemini_network", "The server could not reach the AI service. Please try again in a moment."),
    "model": ("gemini_model", "The configured AI model is not available. The site owner must set GEMINI_MODEL."),
    "bad_request": ("gemini_bad_request", "The AI service could not process this request."),
    "empty": ("gemini_empty", "The AI advisor could not answer that. Please rephrase your question."),
    "unknown": ("gemini_error", "The AI advisor failed to respond."),
}
# When several attempts failed for different reasons, report the one the owner can act on first.
_PRIORITY = ["auth", "model", "quota", "bad_request", "busy", "timeout", "network", "empty", "unknown"]

_lock = threading.Lock()
_client = {"key": None, "obj": None}
_state = {"preferred": None, "last": None}   # model that last worked; outcome of the last call (for the status page)


# ---------------------------------------------------------------------------------------------
# configuration
# ---------------------------------------------------------------------------------------------
def api_key() -> str:
    """The key, tidied: a key pasted into a dashboard often carries a trailing space/newline or quote marks."""
    return str(getattr(settings, "GOOGLE_API_KEY", "") or "").strip().strip("\"'").strip()


def key_format(key: str | None = None) -> str:
    key = api_key() if key is None else key
    if not key:
        return "missing"
    if key.startswith("AIza"):
        return "AIza (classic Google AI Studio key)"
    if key.startswith("AQ."):
        return "AQ. (new Google authentication key)"
    return "unrecognised format"


def models() -> list[str]:
    """GEMINI_MODEL first, then GEMINI_FALLBACK_MODELS, without repeats. The one that worked last goes first."""
    names = [str(getattr(settings, "GEMINI_MODEL", "") or "").strip()]
    fallbacks = getattr(settings, "GEMINI_FALLBACK_MODELS", "") or ""
    names += [m.strip() for m in str(fallbacks).split(",")]
    ordered = []
    for name in names:
        if name and name not in ordered:
            ordered.append(name)
    preferred = _state["preferred"]
    if preferred in ordered:
        ordered.remove(preferred)
        ordered.insert(0, preferred)
    return ordered


def _get_client():
    """One client, reused: it keeps the HTTPS connection to Google warm, which saves ~0.3-1 s on every call."""
    from google import genai

    key = api_key()
    timeout_ms = int(float(getattr(settings, "GEMINI_TIMEOUT", 25)) * 1000)
    marker = (key, timeout_ms, genai.Client)   # a changed key/timeout (or a patched Client in tests) builds a new one
    with _lock:
        if _client["key"] != marker:
            _client["obj"] = genai.Client(api_key=key, http_options={"timeout": timeout_ms})
            _client["key"] = marker
        return _client["obj"]


def _config(types, *, system, json_output, max_tokens, tuned):
    kwargs = {}
    if system:
        kwargs["system_instruction"] = system
    if json_output:
        kwargs["response_mime_type"] = "application/json"
    if max_tokens:
        kwargs["max_output_tokens"] = max_tokens
    level = str(getattr(settings, "GEMINI_THINKING", "") or "").strip()
    if tuned and level:   # "low" = noticeably faster; "MINIMAL" is refused by Gemini 3.7/3.8, so we never use it
        kwargs["thinking_config"] = types.ThinkingConfig(thinking_level=level.upper())
    return types.GenerateContentConfig(**kwargs)


# ---------------------------------------------------------------------------------------------
# classifying failures
# ---------------------------------------------------------------------------------------------
def classify(exc: Exception) -> str:
    """Boil any SDK / network exception down to one kind from MESSAGES."""
    code = getattr(exc, "code", None)
    code = code if isinstance(code, int) else None
    text = f"{exc.__class__.__name__} {exc}".lower()
    if (code in (401, 403) or "api key not valid" in text or "api_key_invalid" in text
            or "access_token_type_unsupported" in text or "permission_denied" in text or "reported as leaked" in text):
        return "auth"
    if code == 404 or ("model" in text and "not found" in text):
        return "model"
    if code == 429 or "resource_exhausted" in text or "quota" in text:
        return "quota"
    if code in (500, 502, 503, 504) or "unavailable" in text or "overloaded" in text or "deadline" in text:
        return "busy"
    if "timeout" in text or "timed out" in text:
        return "timeout"
    if isinstance(exc, OSError) or "connecterror" in text or "name or service" in text or "connection" in text:
        return "network"
    if code == 400 or "invalid_argument" in text:
        return "bad_request"
    return "unknown"


def _fail(kind: str, detail: str | None = None) -> ExternalServiceError:
    code, message = MESSAGES[kind]
    return ExternalServiceError(detail or message, code=code)


def _record(ok: bool, model: str, kind: str = "", message: str = "", ms: int = 0):
    _state["last"] = {"ok": ok, "model": model, "kind": kind, "message": message[:300], "ms": ms, "at": time.time()}


# ---------------------------------------------------------------------------------------------
# the call
# ---------------------------------------------------------------------------------------------
def generate(contents, *, system=None, json_output=False, max_tokens=1500, label="gemini") -> str:
    """Ask Gemini and return its text. Raises ExternalServiceError (502) with a clear, specific message otherwise."""
    if not api_key():
        raise _fail("not_configured")
    from google.genai import types

    client = _get_client()
    deadline = time.monotonic() + float(getattr(settings, "GEMINI_BUDGET", 45))
    problems: list[tuple[str, str]] = []   # (kind, technical text) of everything that failed, for the log

    for model in models():
        tuned, attempts = True, 0
        while attempts < 3 and time.monotonic() < deadline:
            attempts += 1
            started = time.monotonic()
            try:
                response = client.models.generate_content(
                    model=model, contents=contents,
                    config=_config(types, system=system, json_output=json_output, max_tokens=max_tokens, tuned=tuned),
                )
                text = (getattr(response, "text", None) or "").strip()
                ms = int((time.monotonic() - started) * 1000)
                if text:
                    _state["preferred"] = model
                    _record(True, model, ms=ms)
                    log.info("%s ok: model=%s %d ms", label, model, ms)
                    return text
                kind, technical = "empty", "empty answer (blocked or out of tokens)"
            except Exception as exc:  # the SDK raises many types; classify them all
                kind, technical = classify(exc), f"{exc.__class__.__name__}: {exc}"
            ms = int((time.monotonic() - started) * 1000)
            problems.append((kind, technical))
            _record(False, model, kind, technical, ms)
            log.warning("%s failed: model=%s kind=%s after %d ms: %s", label, model, kind, ms, technical[:400])

            if kind == "auth":          # no other model can fix a bad key: stop now and say so
                raise _fail("auth")
            if kind == "bad_request" and tuned:   # e.g. this model refuses thinking_level: retry it with the plain config
                tuned = False
                continue
            if kind in ("busy", "timeout", "network") and attempts == 1:   # worth one more go on the same model
                time.sleep(0.6)
                continue
            break                       # quota / model missing / still failing: try the next model

    kinds = [k for k, _ in problems]
    kind = next((k for k in _PRIORITY if k in kinds), "unknown")
    log.error("%s gave up after %d failed attempt(s): %s", label, len(problems), "; ".join(f"{k}: {t[:120]}" for k, t in problems))
    raise _fail(kind)


# ---------------------------------------------------------------------------------------------
# diagnostics
# ---------------------------------------------------------------------------------------------
def sdk_version() -> str:
    try:
        from importlib.metadata import version

        return version("google-genai")
    except Exception:
        return "not installed"


def _tiny_image() -> bytes:
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (64, 64), (40, 160, 60)).save(buf, "JPEG")
    return buf.getvalue()


def diagnose(*, all_models: bool = False, with_image: bool = False) -> dict:
    """Make one tiny real call per model and report exactly what happened. Never raises."""
    key = api_key()
    report = {
        "configured": bool(key), "key_format": key_format(key), "key_length": len(key),
        "sdk_version": sdk_version(), "model": getattr(settings, "GEMINI_MODEL", ""), "fallbacks": models()[1:],
        "thinking": getattr(settings, "GEMINI_THINKING", ""), "checks": [], "ok": False, "hint": "",
    }
    if not key:
        report["hint"] = "GOOGLE_API_KEY is empty. Set it in .env (local) or in the Render Environment tab (live), then restart."
        return report
    try:
        from google.genai import types

        client = _get_client()
    except Exception as exc:
        report["hint"] = f"The google-genai package could not be loaded ({exc.__class__.__name__}). Run: pip install -U google-genai"
        return report

    for model in models():
        contents = "Reply with the single word: OK"
        if with_image:
            contents = [types.Part.from_bytes(data=_tiny_image(), mime_type="image/jpeg"), "What colour is this image? One word."]
        started = time.monotonic()
        row = {"model": model}
        try:
            response = client.models.generate_content(
                model=model, contents=contents,
                config=_config(types, system=None, json_output=False, max_tokens=64, tuned=True),
            )
            text = (getattr(response, "text", None) or "").strip()
            row.update(ok=bool(text), answer=text[:40], kind="" if text else "empty")
        except Exception as exc:
            kind = classify(exc)
            row.update(ok=False, kind=kind, error=f"{exc.__class__.__name__}: {exc}"[:400])
        row["ms"] = int((time.monotonic() - started) * 1000)
        report["checks"].append(row)
        if row["ok"]:
            report["ok"] = True
            if not all_models:
                break
        elif row["kind"] == "auth":
            break   # the same key is used for every model
    report["hint"] = _hint(report)
    return report


def _hint(report: dict) -> str:
    if report["ok"]:
        return "Gemini works."
    first = report["checks"][0] if report["checks"] else {}
    kind = first.get("kind", "unknown")
    key_note = ""
    if report["key_format"].startswith("AQ."):
        key_note = (" Your key is the new AQ. format: it needs a recent SDK (installed: %s; use google-genai>=2.33) and a Google AI "
                    "Studio project with the Generative Language API enabled." % report["sdk_version"])
    return {
        "auth": "Google rejected the API key. Create a NEW key at https://aistudio.google.com/apikey, paste it with no spaces "
                "or quotes, and make sure the SAME key is set on Render." + key_note,
        "model": "The model name is not available to this key. Set GEMINI_MODEL to a current model (for example gemini-3.6-flash).",
        "quota": "The key works but its free quota is used up (or the model has no free tier). Wait a minute, or enable billing, or "
                 "use another model in GEMINI_FALLBACK_MODELS.",
        "busy": "Google's servers are busy. Try again; the app already retries and falls back to other models.",
        "timeout": "The request timed out. Check the server's internet connection.",
        "network": "This server cannot reach Google. Check the internet connection / firewall.",
        "bad_request": "Google refused the request settings. Update the SDK: pip install -U google-genai",
        "empty": "Gemini answered with nothing. Try again or choose another model.",
    }.get(kind, "Unknown error: read the 'error' text above.")
