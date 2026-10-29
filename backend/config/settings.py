"""
CropGuard backend settings.

All secrets and environment-specific values come from the .env file at the
REPOSITORY ROOT (copy .env.example -> .env). Never commit .env.
"""
import os
from datetime import timedelta
from pathlib import Path

import django_mongodb_backend
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent  # .../backend
REPO_ROOT = BASE_DIR.parent
load_dotenv(REPO_ROOT / ".env")


def env_list(name: str, default: str = "") -> list[str]:
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


# --- Core -------------------------------------------------------------------
ON_RENDER = os.getenv("RENDER") == "true"  # Render sets RENDER=true on every service it runs
# Local development defaults to DEBUG on; on Render it defaults to OFF (set DJANGO_DEBUG=True there only to debug).
DEBUG = os.getenv("DJANGO_DEBUG", "False" if ON_RENDER else "True") == "True"
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-only-insecure-key-replace-me-in-dotenv")
if not DEBUG and SECRET_KEY == "dev-only-insecure-key-replace-me-in-dotenv":
    raise ImproperlyConfigured("Set DJANGO_SECRET_KEY when DJANGO_DEBUG is not True.")
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
if os.getenv("RENDER_EXTERNAL_HOSTNAME"):  # e.g. cropguarv1.onrender.com: Render tells us our own address
    ALLOWED_HOSTS.append(os.environ["RENDER_EXTERNAL_HOSTNAME"])
# The address of the website (frontend) that is allowed to call this API. No trailing slash.
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://cropguard-9fmd.onrender.com").rstrip("/")

INSTALLED_APPS = [
    "config.apps.MongoAdminConfig",
    "config.apps.MongoAuthConfig",
    "config.apps.MongoContentTypesConfig",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_mongodb_backend",
    # third party
    "rest_framework",
    "corsheaders",
    # CropGuard apps
    "apps.core",
    "apps.accounts",
    "apps.detection",
    "apps.advisory",
    "apps.assistant",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",  # must stay first
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # serves the admin's CSS/JS in production
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# --- MongoDB ----------------------------------------------------------------
DATABASES = {
    "default": django_mongodb_backend.parse_uri(
        os.getenv("MONGODB_URI", "mongodb://localhost:27017"),
        db_name=os.getenv("MONGODB_NAME", "cropguard"),
    )
}
DATABASES["default"].setdefault("OPTIONS", {}).setdefault("serverSelectionTimeoutMS", 5000)
DATABASE_ROUTERS = ["django_mongodb_backend.routers.MongoRouter"]
DEFAULT_AUTO_FIELD = "django_mongodb_backend.fields.ObjectIdAutoField"
MIGRATION_MODULES = {
    "admin": "mongo_migrations.admin",
    "auth": "mongo_migrations.auth",
    "contenttypes": "mongo_migrations.contenttypes",
}

# --- Auth -------------------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework_simplejwt.authentication.JWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    # Rate limits ("N/min" or "N/hour"). Views opt in with throttle_scope; each farmer (or, when
    # signed out, each IP address) gets their own counter. Override any of them in .env.
    "DEFAULT_THROTTLE_RATES": {
        "assistant": os.getenv("ASSISTANT_RATE", "30/min"),   # AI chat questions
        "login": os.getenv("LOGIN_RATE", "20/min"),           # sign-in attempts (slows password guessing)
        "register": os.getenv("REGISTER_RATE", "20/hour"),    # new accounts (generous: shared phone networks)
        "upload": os.getenv("UPLOAD_RATE", "60/hour"),        # photo checks (each one runs the model)
        "verify": os.getenv("AI_VERIFY_RATE", "60/hour"),      # Gemini second opinion on a photo (one per check)
        "ai": os.getenv("AI_RATE", "30/hour"),                # treatment advice + weather advice (Gemini)
        "weather": os.getenv("WEATHER_RATE", "120/hour"),     # forecast lookups (OpenWeather)
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(os.getenv("JWT_ACCESS_MINUTES", "60"))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(os.getenv("JWT_REFRESH_DAYS", "7"))),
    "UPDATE_LAST_LOGIN": False,
}

# --- CORS (the frontend runs on a different port during development) ---------
CORS_ALLOWED_ORIGINS = [
    origin.rstrip("/")
    for origin in env_list(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:5500,http://127.0.0.1:5500,http://localhost:8080,http://127.0.0.1:8080",
    )
]
if FRONTEND_URL not in CORS_ALLOWED_ORIGINS:
    CORS_ALLOWED_ORIGINS.append(FRONTEND_URL)

# Django's admin login (a form post) must come from an address we trust.
CSRF_TRUSTED_ORIGINS = [FRONTEND_URL, *env_list("CSRF_TRUSTED_ORIGINS")]
if os.getenv("RENDER_EXTERNAL_HOSTNAME"):
    CSRF_TRUSTED_ORIGINS.append(f"https://{os.environ['RENDER_EXTERNAL_HOSTNAME']}")

if not DEBUG:
    # Render ends the HTTPS connection at its edge and forwards plain HTTP to us. Without this, Django thinks every
    # request is http:// and builds http:// photo links, which the browser blocks on the https:// website.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# --- Static & media ---------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
# Uploaded leaf photos. On Render the normal disk is wiped on every deploy/restart: to keep photos, attach a
# persistent disk (e.g. mounted at /var/data) and set MEDIA_ROOT=/var/data/media.
MEDIA_ROOT = Path(os.getenv("MEDIA_ROOT") or BASE_DIR / "media")
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 MB

# --- Logging (Render shows whatever is printed to the console) --------------
# With DEBUG off Django prints no tracebacks by default; this keeps 500 errors visible in Render's Logs tab.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": os.getenv("LOG_LEVEL", "INFO")},
}

# --- i18n -------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Kigali"
USE_I18N = True
USE_TZ = True

# --- ML / AI integrations ---------------------------------------------------
# One detector per crop. A crop is "available" as soon as its weights file exists, so the
# cassava model switches on by itself the day ml/weights/cassava.pt is added.
CROP_MODELS = {
    "maize": {
        "name": "Maize",
        # YOLO_MODEL_PATH is the old name for the maize model and still works
        "path": Path(os.getenv("YOLO_MODEL_MAIZE_PATH") or os.getenv("YOLO_MODEL_PATH") or REPO_ROOT / "ml" / "weights" / "best.pt"),
    },
    "cassava": {
        "name": "Cassava",
        "path": Path(os.getenv("YOLO_MODEL_CASSAVA_PATH") or REPO_ROOT / "ml" / "weights" / "cassava.pt"),
    },
}
LABELS_PATH = Path(os.getenv("LABELS_PATH") or REPO_ROOT / "ml" / "labels.json")
YOLO_CONF = float(os.getenv("YOLO_CONF", "0.5"))    # minimum confidence to report a detection
YOLO_IMGSZ = int(os.getenv("YOLO_IMGSZ", "640"))    # the maize model was trained at 640
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "8"))

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
# When Gemini disagrees about WHICH DISEASE (same crop), the detector keeps its answer if it is at least this sure.
# Below it, Gemini wins only if it is itself highly certain. (Crop identity is always Gemini's call.)
VERIFY_DETECTOR_TRUST = float(os.getenv("VERIFY_DETECTOR_TRUST", "0.80"))
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
