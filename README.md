# CropGuard

A web app that helps Rwandan farmers check **maize and cassava** leaves for disease from a photo, get AI treatment advice, ask an AI assistant any farming question, and get a 24-hour weather plan (irrigate? spray?) in Kinyarwanda, English or Français.

**Stack:** HTML/CSS/JavaScript frontend · Django REST API · MongoDB · YOLOv8 detectors · Gemini + OpenWeatherMap

## Project layout

```
CropGuard/
├── backend/                 Django REST API  (teammate)
│   ├── config/              settings, urls
│   └── apps/
│       ├── accounts/        farmer accounts + JWT login
│       ├── detection/       photo -> YOLO -> saved result (one model per crop)
│       │   ├── crops.py            which crops exist, model files, readable disease names
│       │   └── services/yolo.py    model loading and inference
│       ├── advisory/        weather + Gemini advice
│       ├── assistant/       "Ask the AI": farming Q&A chat (Gemini)
│       └── core/            health check, shared exceptions
├── frontend/                HTML + CSS + JS, no build step  (you)
│   ├── index, story, login, register, dashboard, detect, history, advisory, assistant, account  (.html)
│   ├── css/  js/  assets/   see frontend/README.md
│   └── assets/data/story.json   survey numbers behind the "Our story" charts
├── ml/
│   ├── weights/best.pt      maize detector       (classes MLB, MSV)
│   ├── weights/cassava.pt   cassava detector     (3 diseases + Healthy)
│   └── labels.json          class code -> readable name
├── data/                    survey microdata (NOT in Git) and the script that turns it into story.json
├── docs/                    API.md (the contract) and GIT_WORKFLOW.md
├── run-backend.bat/.sh      starts the backend
├── run-frontend.bat/.sh     starts the frontend
├── docker-compose.yml       local MongoDB
└── .env.example             copy to .env
```

## Run it locally

You need two things running: the **backend** (the API and the detectors) and the **frontend** (the pages).

### 1. MongoDB and keys
```bash
cp .env.example .env        # fill in GOOGLE_API_KEY and OPENWEATHER_API_KEY
docker compose up -d        # MongoDB (or put a MongoDB Atlas link in .env)
```

### 2. Backend
Double-click **`run-backend.bat`** (Windows) or run `./run-backend.sh`. It creates the virtual environment, installs the requirements, runs the migrations and starts the API at http://127.0.0.1:8000. (The first install is large because it includes PyTorch for the detectors.)

Check the maize detector on a real photo, without the website:
```bash
cd backend && python manage.py try_detector ../path/to/maize-leaf.jpg
cd backend && python manage.py try_detector ../path/to/cassava-leaf.jpg --crop cassava
```

### 3. Frontend
Double-click **`run-frontend.bat`** (Windows) or run `./run-frontend.sh`. It opens http://127.0.0.1:5500.
**Do not open the .html files by double-clicking them**: browsers block the page scripts on `file://` addresses and the pages look broken.

The frontend talks to the real backend by default. To look around with sample data and no backend, add `?mock=1` to any page address (`?mock=0` to leave demo mode).

### 4. Tests (backend)
```bash
cd backend && python manage.py test
```

## What each part does
- **Check a plant:** choose Maize or Cassava, upload a photo, see the framed disease (or a healthy leaf) and ask for treatment advice. A crop switches from "Coming soon" to available by itself when its weights file exists in `ml/weights/`.
- **Weather advice:** 24-hour forecast chart plus advice, with Kinyarwanda / English / Français tabs right on the result.
- **Ask the AI:** farming questions answered by Gemini in the farmer's language. The conversation stays in the browser; the server stores nothing.
- **Our story:** the case for CropGuard, drawn from the AHS2024 survey. Rebuild its numbers with `python data/build_story_data.py` (see `data/README.md`).

## Who works where
| Person | Folder | Reads | Never edits without a PR |
|--------|--------|-------|--------------------------|
| Backend dev | `backend/` | `docs/API.md` | `frontend/` |
| Frontend dev | `frontend/` | `docs/API.md` | `backend/` |

See [`docs/GIT_WORKFLOW.md`](docs/GIT_WORKFLOW.md) for the branch and pull-request routine.

## Putting it online
Both parts run on Render: the website (static site) at <https://cropguard-9fmd.onrender.com> and the backend at
<https://cropguarv1.onrender.com>. Pushing to `main` redeploys them. The exact dashboard settings, environment variables
and troubleshooting are in [`docs/DEPLOY.md`](docs/DEPLOY.md).

## Next steps (suggested)
1. Run the backend against a real MongoDB: `migrate`, then `python manage.py test` (the database tests have not been run against a live MongoDB yet).
2. Try both detectors on real field photos with `try_detector` and tune `YOLO_CONF` in `.env`.
3. Add rate limiting on the weather endpoint, and make `DELETE` also remove the image file.
