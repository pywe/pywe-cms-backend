"""
Django settings for pywe-cms-backend (workspace sites, manager auth, public CMS API).
"""

import logging
import os
from datetime import timedelta
from pathlib import Path

import dj_database_url
from corsheaders.defaults import default_headers
from dotenv import load_dotenv

# ---------------------------------------------------------
# Base paths
# ---------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_NAME = "pywe_cms_backend"
ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")

load_dotenv(BASE_DIR / ".env")
load_dotenv(BASE_DIR / "dev.env")

# ---------------------------------------------------------
# Security
# ---------------------------------------------------------
SECRET_KEY = os.environ.get("SECRET_KEY")
DEBUG = os.environ.get("DEBUG", "true").lower() in ("1", "true", "yes")

if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "django-insecure-dev-only-change-me"
    else:
        raise ValueError("SECRET_KEY must be set when DEBUG is false")

ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get("ALLOWED_HOSTS", "*").split(",")
    if h.strip()
]

CSRF_TRUSTED_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "CSRF_TRUSTED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000,"
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:8000,http://127.0.0.1:8000",
    ).split(",")
    if o.strip()
]

# ---------------------------------------------------------
# Installed Apps
# ---------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # third party
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "drf_yasg",
    "django_filters",
    "phonenumber_field",
    # my apps
    "core",
]

# ---------------------------------------------------------
# Middleware
# ---------------------------------------------------------
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "pywe_cms_backend.urls"

# ---------------------------------------------------------
# Templates
# ---------------------------------------------------------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "pywe_cms_backend.wsgi.application"

# ---------------------------------------------------------
# Database
# ---------------------------------------------------------
DATABASES = {
    "default": dj_database_url.config(
        default=os.environ.get("DATABASE_URL", f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),
        conn_max_age=30,
        conn_health_checks=True,
    )
}

# ---------------------------------------------------------
# Authentication
# ---------------------------------------------------------
# AdminUser is Django admin / staff only (AUTH_USER_MODEL). APIs authenticate
# merchants and customers via Account (MemberAuthentication + JWT).
AUTH_USER_MODEL = "core.AdminUser"
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
AUTHENTICATION_BACKENDS = [f"{PROJECT_NAME}.authentication.BackendAuthentication"]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------
# REST Framework
# ---------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        f"{PROJECT_NAME}.authentication.MemberAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_PAGINATION_CLASS": "apis.pagination.StandardPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
}

# ---------------------------------------------------------
# JWT Config
# ---------------------------------------------------------
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        days=365 if os.environ.get("JWT_LONG_LIVED") else 1
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "TOKEN_REFRESH_SERIALIZER": "apis.jwt_serializers.AccountAwareTokenRefreshSerializer",
}

# ---------------------------------------------------------
# CORS
# ---------------------------------------------------------
CORS_ALLOW_ALL_ORIGINS = DEBUG
# Manager app and public site clients may send workspace/site headers; public API uses X-CMS-API-Key.
CORS_ALLOW_HEADERS = (
    *default_headers,
    "x-cms-api-key",
    "x-site-id",
    "x-site-slug",
    "x-workspace-slug",
)
CORS_ALLOWED_ORIGINS = [
    "https://cms.pywe.org",
    "https://account.pywe.org",
    "https://pywe.org",
    "https://www.pywe.org",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
] + (
    [origin for origin in os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",") if origin]
    if not DEBUG
    else []
)

# ---------------------------------------------------------
# Static & Media
# ---------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"

# Docker volumes:
#   - docker-compose.prod.yml (prod): media_data:/app/media
# Local dev: project root / media
if os.environ.get("DOCKER_ENV") == "true":
    MEDIA_ROOT = Path("/app/media")
elif Path("/code/media").exists():
    MEDIA_ROOT = Path("/code/media")
else:
    MEDIA_ROOT = BASE_DIR / "media"

try:
    MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
except (OSError, PermissionError) as exc:
    logging.warning("Could not create media directory at %s: %s", MEDIA_ROOT, exc)

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# ---------------------------------------------------------
# Internationalization
# ---------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Accra"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------
# Logging
# ---------------------------------------------------------
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
        "simple": {"format": "{levelname} {message}", "style": "{"},
    },
    "handlers": {
        "file": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": LOG_DIR / "django.log",
            "formatter": "verbose",
        },
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["file", "console"],
            "level": "INFO",
            "propagate": True,
        },
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------
# Pywe CMS settings
# ---------------------------------------------------------
BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")

PHONENUMBER_DEFAULT_REGION = os.environ.get("PHONENUMBER_DEFAULT_REGION", "GH")

# SMS (manager OTP / Pywe gateway). Leave keys empty in dev to log OTPs only.
SMS_API_BASE_URL = os.environ.get("SMS_API_BASE_URL", "https://pushr.pywe.org")
SMS_API_KEY_PUBLIC = os.environ.get("SMS_API_KEY_PUBLIC", "")
SMS_API_KEY_SECRET = os.environ.get("SMS_API_KEY_SECRET", "")
SMS_SENDER_ID = os.environ.get("SMS_SENDER_ID", "Pywe")
SMS_BRAND_NAME = os.environ.get("SMS_BRAND_NAME", "Pywe")
SMS_GATEWAY_CONFIGURED = bool(SMS_API_BASE_URL and SMS_API_KEY_PUBLIC and SMS_API_KEY_SECRET)

# Manager dashboard link in transactional SMS (utils/sms/templates.py).
STORE_OWNER_DASHBOARD_URL = os.environ.get(
    "STORE_OWNER_DASHBOARD_URL",
    "https://account.pywe.org/dashboard",
)


def _derive_manager_app_url(dashboard_url: str) -> str:
    url = (dashboard_url or "").rstrip("/")
    if url.endswith("/dashboard"):
        return url[: -len("/dashboard")]
    return url or "https://account.pywe.org"


STORE_OWNER_APP_URL = os.environ.get(
    "STORE_OWNER_APP_URL",
    _derive_manager_app_url(STORE_OWNER_DASHBOARD_URL),
)
MERCHANT_SMS_DEV_SHOW_CODE = os.environ.get("MERCHANT_SMS_DEV_SHOW_CODE", "false").lower() in (
    "1",
    "true",
    "yes",
)

# ---------------------------------------------------------
# Platform email (Resend) — optional until transactional email is wired
# ---------------------------------------------------------
USE_RESEND = os.environ.get("USE_RESEND", "true").lower() in ("1", "true", "yes")
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "").strip()
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "").strip()

# ---------------------------------------------------------
# Cache
# ---------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}
