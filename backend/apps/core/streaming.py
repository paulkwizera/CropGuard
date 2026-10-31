"""Server-Sent Events: send an AI answer to the page piece by piece, as Gemini writes it.

The page reads these events with fetch():
    event: chunk   data: {"t": "some new words"}      (many times)
    event: done    data: {"text": "the whole answer"}  (once, at the end)
    event: error   data: {"detail": "...", "code": "gemini_busy"}   (instead of done, if something failed)
Anything wrong with the REQUEST itself (bad input, not signed in, too many requests) is answered as a normal JSON
error before the stream starts, exactly like the non-streaming endpoints.
"""
import json
import logging

from django.http import StreamingHttpResponse
from rest_framework.exceptions import APIException

log = logging.getLogger("cropguard.streaming")


def event(name: str, data: dict) -> str:
    return f"event: {name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def text_events(chunks, on_done=None):
    """Turn an iterator of text pieces into SSE events. `on_done(full_text)` runs once, after the last piece."""
    yield ": stream open\n\n"   # a first line right away, so proxies start passing data through
    parts = []
    try:
        for piece in chunks:
            parts.append(piece)
            yield event("chunk", {"t": piece})
    except APIException as exc:
        yield event("error", {"detail": str(exc.detail), "code": str(exc.get_codes())})
        return
    except Exception:
        log.exception("stream failed")
        yield event("error", {"detail": "The AI advisor failed to respond.", "code": "gemini_error"})
        return
    text = "".join(parts)
    if on_done:
        try:
            on_done(text)
        except Exception:   # the farmer already has the answer; a failed save must not turn it into an error
            log.exception("could not save the streamed answer")
    yield event("done", {"text": text})


def response(events) -> StreamingHttpResponse:
    resp = StreamingHttpResponse(events, content_type="text/event-stream; charset=utf-8")
    resp["Cache-Control"] = "no-cache, no-transform"
    resp["X-Accel-Buffering"] = "no"   # nginx-style proxies: do not hold the answer back
    return resp
