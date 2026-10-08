# CropGuard

A web app that helps Rwandan farmers diagnose **maize leaf diseases** from a photo, get AI treatment advice, and get a 24-hour weather plan (irrigate? spray?).

**Stack:** HTML/CSS/JavaScript frontend · Django REST API · MongoDB · YOLOv8 (ultralytics) · Gemini + OpenWeatherMap

## Project layout

```
CropGuard/
├── backend/                 Django REST API  (teammate)
│   ├── config/              settings, urls, wsgi/asgi
│   ├── apps/
│   │   ├── core/            health check, shared exceptions
│   │   ├── accounts/        farmer accounts + JWT login
│   │   ├── detection/       upload photo → YOLO → saved results
│   │   │   └── services/yolo.py     model loading & inference
│   │   └── advisory/        weather + Gemini advice
│   │       └── services/            weather.py, advisor.py
│   ├── mongo_migrations/    required by django-mongodb-backend
│   ├── manage.py
│   └── requirements.txt
├── frontend/                HTML + CSS + JS, no build step  (you)
│   ├── index.html login.html register.html detect.html history.html advisory.html
│   ├── css/                 tokens.css (colours/fonts) · base.css · components.css
│   └── js/
│       ├── config.js        API URL + USE_MOCK switch
│       ├── api.js           every backend call lives here
│       ├── mock.js          fake data so you can work before the API exists
│       ├── auth.js · ui.js  token storage, shared header, toasts, helpers
│       └── pages/           one script per page
├── ml/                      model weights, training samples, legacy scripts
├── docs/
│   ├── API.md               ← the contract between frontend and backend
│   └── GIT_WORKFLOW.md      branches and rules for working as a pair
├── .github/                 CI, PR template, CODEOWNERS
├── docker-compose.yml       local MongoDB
├── .env.example             copy to .env
└── README.md
```

## Run it locally

### 1. Backend (needs Python 3.12 and MongoDB)
```bash
cp .env.example .env                 # then fill in the keys you have
docker compose up -d                 # starts MongoDB (or use a MongoDB Atlas URI in .env)

cd backend
python -m venv venv
source venv/bin/activate             # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser     # optional, for /admin/
python manage.py runserver           # http://127.0.0.1:8000/api/health/
```

### 2. Frontend (no install)
```bash
cd frontend
python -m http.server 5500           # open http://127.0.0.1:5500
```
(or use the VS Code **Live Server** extension on port 5500). Pages use ES modules, so open them through a server, not by double-clicking the file.

`frontend/js/config.js` starts with `USE_MOCK: true`, so every page works with sample data. Set it to `false` once the backend is running.

### 3. Tests (backend)
```bash
cd backend && python manage.py test
```

## Who works where
| Person | Folder | Reads | Never edits without a PR |
|--------|--------|-------|--------------------------|
| Backend dev | `backend/` | `docs/API.md` | `frontend/` |
| Frontend dev | `frontend/` | `docs/API.md` | `backend/` |

See [`docs/GIT_WORKFLOW.md`](docs/GIT_WORKFLOW.md) for the branch and pull-request routine.

## Backend to-do (suggested order)
1. Run it against a real MongoDB: `migrate`, then the tests in `apps/*/tests.py` (they were written but not yet run against a live database).
2. Confirm the detection flow end-to-end with `ml/weights/best.pt` and tune `YOLO_CONF`.
3. Add rate limiting on the AI endpoints, and a `DELETE` that also removes the image file.
4. Deployment settings (`DJANGO_DEBUG=False`, `ALLOWED_HOSTS`, Gunicorn, media storage).
