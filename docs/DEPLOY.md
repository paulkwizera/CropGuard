# Deploying CropGuard on Render

CropGuard runs as **two Render services** built from this one GitHub repo:

| Part | Render service type | Address |
|---|---|---|
| Website (`frontend/`) | **Static Site** | https://cropguard-9fmd.onrender.com |
| Backend (`backend/`) | **Web Service** (Python 3) | https://cropguarv1.onrender.com |

Everything in the code is already prepared: the website finds the backend by itself (`frontend/js/config.js`), the backend
allows the website (CORS), serves photos over https, runs in production mode on Render, and shows errors in the Logs tab.
**You only have to set the dashboard values below once.** After that, every `git push` to `main` redeploys.

## 1. MongoDB Atlas (once)
1. Atlas, then **Network Access**, then **Add IP address**, then **Allow access from anywhere** (`0.0.0.0/0`).
   Render's servers have no fixed address, so Atlas cannot be limited to one.
2. **Database Access**: a user with a password (avoid `@ : / ?` in it, or URL-encode them).
3. **Connect, Drivers**: copy the string, which looks like `mongodb+srv://USER:PASSWORD@cluster0.xxxxx.mongodb.net/`.

## 2. Backend: Web Service `cropguarv1`
**Settings tab**

| Field | Value |
|---|---|
| Runtime | Python 3 |
| Root Directory | *(leave empty)* |
| Build Command | `bash backend/build.sh` |
| Start Command | `bash backend/start.sh` |
| Health Check Path | `/api/health/` |
| Auto-Deploy | Yes (branch `main`) |

**Environment tab**

| Key | Value |
|---|---|
| `DJANGO_SECRET_KEY` | click **Generate** (required: the app refuses to start without it) |
| `MONGODB_URI` | the Atlas string from step 1 |
| `MONGODB_NAME` | `cropguard` |
| `GOOGLE_API_KEY` | your Gemini key (advice, assistant and the second opinion need it) |
| `OPENWEATHER_API_KEY` | your OpenWeather key |
| `DJANGO_DEBUG` | *(do not set; it is False on Render)* |

Optional: `GEMINI_MODEL`, `YOLO_CONF`, `FRONTEND_URL` (only if the website's address changes), `LOG_LEVEL`.
Do **not** set `PYTHON_VERSION` unless the build log shows the wrong Python: the repo pins 3.12 in `.python-version`, and an
environment variable would override it.

### Memory (important)
The detectors load PyTorch and two YOLO models. The build installs the small CPU-only PyTorch and the server runs one worker
to keep memory low, but a 512 MB instance (Free and Starter) may still run out. If the Logs show
**"Out of memory"** or the service restarts during a check, upgrade the instance to **Standard (2 GB)**.
Prices and free-tier rules change, so check <https://render.com/pricing>. Free instances also go to sleep after 15 minutes
without visitors, so the first request afterwards takes up to a minute (the website wakes the backend as soon as a page opens).

### Keeping leaf photos (optional, paid instances only)
Render wipes the normal disk on every deploy and restart. Without a disk the results and history stay (they live in MongoDB)
but the **photos disappear** (thumbnails are then hidden). To keep them: **Disks, Add disk**, mount path `/var/data`,
1 GB, then add the environment variable `MEDIA_ROOT` = `/var/data/media`. Free instances cannot have disks.

## 3. Website: Static Site `cropguard-9fmd`
| Field | Value |
|---|---|
| Root Directory | *(leave empty)* |
| Build Command | `echo "static site, nothing to build"` |
| Publish Directory | `frontend` |
| Auto-Deploy | Yes (branch `main`) |

No environment variables. If the backend's address ever changes, edit `LIVE_API` in `frontend/js/config.js` (and
`FRONTEND_URL` on the backend if the website's address changes).

## 4. Check that it works
1. Open <https://cropguarv1.onrender.com/api/health/>. The first call may take a minute. You should see
   `{"status":"ok","mongodb":"ok"}`. If `mongodb` says `unreachable`, fix `MONGODB_URI` / Atlas Network Access.
2. Open <https://cropguard-9fmd.onrender.com>, register, log in.
3. **Check a plant** with a maize and a cassava photo. A result with a photo and the *Second opinion* card means the model,
   Gemini, MongoDB and photo storage all work.

## 5. If something is wrong (look at the **Logs** tab of the backend first)
| What you see | Likely cause and fix |
|---|---|
| "Cannot reach the server" on the website | The backend is still waking up (wait a minute and retry), or it failed to start (see Logs). |
| Browser console: CORS error | The website's address differs from `FRONTEND_URL` (default `https://cropguard-9fmd.onrender.com`). Set `FRONTEND_URL` on the backend. |
| Every request is `400 Bad Request`, log says `DisallowedHost` | Add the backend's address to `DJANGO_ALLOWED_HOSTS` (normally automatic). |
| Deploy fails: `ImproperlyConfigured: Set DJANGO_SECRET_KEY` | Add `DJANGO_SECRET_KEY` (step 2). |
| Build fails: `libGL.so.1` | The Build Command must be `bash backend/build.sh` (it installs the headless OpenCV). |
| "Out of memory" / the service restarts when checking a plant | Upgrade to Standard (2 GB). |
| Second opinion / Get advice / Ask the AI / Weather advice fail | Open `https://cropguarv1.onrender.com/api/health/ai/`: it makes one real Gemini call and says what is wrong (missing key, rejected key, model name, quota, ...). The Render **Logs** tab also shows a line `gemini failed: model=... kind=...` for every failed call. Then fix `GOOGLE_API_KEY` / `GEMINI_MODEL` in the Environment tab (no quotes, no spaces) and the service restarts by itself. |
| `kind=auth` in the logs, or "AI service rejected its API key" | The key is wrong, restricted or the Generative Language API is off for its project. Create a new key at <https://aistudio.google.com/apikey>, paste it on Render, and make sure `google-genai>=2.33` is installed (new `AQ.` keys need a recent SDK: use **Manual Deploy, Clear build cache & deploy**). |
| Photos vanish after a deploy | Attach a disk and set `MEDIA_ROOT` (see above). |
| Health says `mongodb: unreachable` | Atlas Network Access must allow `0.0.0.0/0`; check the user and password in `MONGODB_URI`. |
| Detection fails with "model file missing" | `ml/weights/best.pt` and `cassava.pt` must be committed (they are tracked in git). |

## What the code does for you
* `backend/build.sh`: installs the dependencies (CPU-only PyTorch), swaps OpenCV for its headless build, collects static files.
* `backend/start.sh`: runs the database migrations, then starts Gunicorn.
* `backend/gunicorn.conf.py`: 1 worker with 4 threads, a 180 s timeout (a check plus Gemini can take a while), logs to Render.
* `.python-version`: Python 3.12 (the version CI tests with).
* Production-safe settings: `DEBUG` off on Render, HTTPS-aware links, CORS only for the website, admin login
  protected with CSRF, random unguessable photo file names, error logging.
