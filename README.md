# CropGuard

A web app that helps Rwandan farmers check **maize and cassava** leaves for disease from a photo, get AI treatment advice, ask an AI assistant any farming question, and get a 24-hour weather plan (irrigate? spray?) in Kinyarwanda, English or Français.

**Stack:** HTML/CSS/JavaScript frontend · Django REST API · MongoDB · YOLOv8 detectors · Gemini + OpenWeatherMap

## Project layout

```
CropGuard/
├── backend/                 Django REST API  (Backend developer)
│   ├── config/              settings, urls
│   └── apps/
│       ├── accounts/        farmer accounts + JWT login
│       ├── detection/       photo -> YOLO -> saved result (one model per crop)
│       │   ├── crops.py            which crops exist, model files, readable disease names
│       │   └── services/yolo.py    model loading and inference
│       ├── advisory/        weather + Gemini advice
│       ├── assistant/       "Ask the AI": farming Q&A chat (Gemini)
│       └── core/            health check, shared exceptions
├── frontend/                HTML + CSS + JS, no build step  (Frontend developer)
│   ├── index, story, login, register, dashboard, detect, history, advisory, assistant, account  (.html)
│   ├── css/  js/  assets/   see frontend/README.md
│   └── assets/data/story.json   survey numbers behind the "Our story" charts
├── ml/
│   ├── weights/best.pt      maize detector       (classes MLB, MSV)
│   ├── weights/cassava.pt   cassava detector     (3 diseases + Healthy)
│   └── labels.json          class code -> readable name
├── data/                    survey microdata (tracked with Git LFS) and the script that turns it into story.json
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

## How to use it
1. Register or sign in, and pick your language (Kinyarwanda, English, Français).
2. **Check a plant:** upload a photo of one leaf, read the result, and tap *Get advice*. CropGuard detects the crop automatically, or you can choose Maize or Cassava yourself.
3. **History:** filter or sort past checks, open one for details, or delete it.
4. **Weather:** choose your district to see the forecast and advice.
5. **Ask the AI:** type any farming question.

## What each part does
- **Check a plant:** upload a photo and the crop is detected automatically (or choose Maize or Cassava), then see the framed disease (or a healthy leaf) and ask for treatment advice. A crop switches from "Coming soon" to available by itself when its weights file exists in `ml/weights/`.
- **Weather advice:** 24-hour forecast chart plus advice, with Kinyarwanda / English / Français tabs right on the result.
- **Ask the AI:** farming questions answered by Gemini in the farmer's language. The conversation stays in the browser; the server stores nothing.
- **Our story:** the case for CropGuard, drawn from the AHS2024 survey. Rebuild its numbers with `python data/build_story_data.py` (see `data/README.md`).

## What the app communicates
- **Check result:** the detected disease (or healthy leaf), a confidence percentage, and a frame on the photo showing where it was found. It is a guide, not a diagnosis.
- **Dashboard:** total checks, problems found, most common disease, last check, recent checks and today's weather.
- **Weather advice:** a 24-hour temperature and rain chart, plus a plain-language call on whether to irrigate or spray.
- **Our story:** more than half of crop plots (52.6%) had a smaller harvest than the season before (55.8% for maize, 43.6% for cassava), and catching disease early is one of the few things a farmer can still do while the crop is growing.

## Data used
- **Leaf photos (from users):** uploaded by farmers, saved with the detection result (crop, disease, confidence) so they can see their history. Only the owner can see them.
- **Disease detectors:** YOLOv8 models trained on public plant-disease image datasets for maize (MLB, MSV) and cassava (3 diseases + healthy).
- **Weather:** OpenWeatherMap 5-day / 3-hour forecast; the app uses the next 24 hours for the farmer's district.
- **Survey data:** National Institute of Statistics of Rwanda (NISR) Agricultural Household Survey 2024 (AHS2024), summarised for the "Our story" page.
- **AI text:** Gemini writes treatment advice and weather advice from the result or forecast.

## Rate limits
The expensive actions are limited so the API and the paid services behind it are not overloaded. Each signed-in farmer gets their own counter (signed-out requests are counted per IP address). Every limit can be changed in `.env`.

| Action | Default | `.env` setting |
|--------|---------|----------------|
| Sign in | 20 per minute | `LOGIN_RATE` |
| Create an account | 20 per hour | `REGISTER_RATE` |
| Photo check (runs the model) | 60 per hour | `UPLOAD_RATE` |
| Treatment advice and weather advice (Gemini) | 30 per hour | `AI_RATE` |
| Weather forecast lookup | 120 per hour | `WEATHER_RATE` |
| Ask the AI (chat) | 30 per minute | `ASSISTANT_RATE` |

Listing, viewing and deleting past checks are not limited.

## Who works where
| Person | Folder | Reads | Never edits without a PR |
|--------|--------|-------|--------------------------|
| Backend developer | `backend/` | `docs/API.md` | `frontend/` |
| Frontend developer | `frontend/` | `docs/API.md` | `backend/` |

See [`docs/GIT_WORKFLOW.md`](docs/GIT_WORKFLOW.md) for the branch and pull-request routine.

## Next steps (suggested)
1. Try both detectors on real field photos with `try_detector` and tune `YOLO_CONF` in `.env`.
2. Make `DELETE` also remove the image file.