"""
Gunicorn settings for Render. Gunicorn loads this file by itself when it is started from the backend folder,
so it applies whatever start command the service uses.
"""
import os

bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"   # Render tells us the port in $PORT

# ONE worker: every worker loads its own copy of PyTorch and the YOLO models (hundreds of MB each).
# Threads let that one worker serve several farmers at the same time.
workers = int(os.getenv("GUNICORN_WORKERS", "1"))
threads = int(os.getenv("GUNICORN_THREADS", "4"))

# A check can take a while: the model runs, then Gemini double-checks (up to ~45 s). Gunicorn's default of 30 s
# would kill the worker in the middle of it.
timeout = 180
graceful_timeout = 60   # a planned restart waits this long for a running answer (Gemini can take up to ~45 s)
keepalive = 5

# Restart the worker after a few hundred requests: PyTorch slowly keeps memory, and a planned restart is invisible
# (the next check just takes a few seconds longer) while Render's out-of-memory restart drops everyone's request.
max_requests = int(os.getenv("GUNICORN_MAX_REQUESTS", "300"))
max_requests_jitter = 50

accesslog = "-"   # Render's Logs tab shows what is printed
errorlog = "-"

# Small servers have 0.5-1 CPU: one math thread is the fastest and the lightest on memory.
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")


def post_worker_init(worker):
    """Each time a worker starts (also after a planned restart), load the detectors in the background."""
    if os.getenv("YOLO_WARMUP", "1") != "1":
        return
    import threading

    def run():
        try:
            from apps.detection.services import yolo

            yolo.warm_up()
        except Exception:   # never stop the server from starting because of this
            pass

    threading.Thread(target=run, name="yolo-warmup", daemon=True).start()
