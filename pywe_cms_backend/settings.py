"""Django settings for pywe-cms-backend (blueprint-aligned)."""

import os
from datetime import timedelta
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")
load_dotenv(BASE_DIR / "dev.env")

DEBUG = os.environ.get("DEBUG", "true").lower() in ("1", "true", "yes")

SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "django-insecure-dev-only-change-me"
    else:
        raise ValueError("SECRET_KEY must be set when DEBUG is false")

ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if h.strip()
]

ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")
DOCKER_ENV = os.environ.get("DOCKER_ENV", "false").lower() in ("1", "true", "yes")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "django_filters",
    "phonenumber_field",
    "drf_yasg",
    "core",
]

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

WSGI_APPLICATION = "pywe_cms_backend.wsgi.application"

DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


SMS_API_BASE_URL = os.environ.get("SMS_API_BASE_URL", "https://pushr.pywe.org")
SMS_API_KEY_PUBLIC = os.environ.get("SMS_API_KEY_PUBLIC", "276e1b326439229f")
SMS_API_KEY_SECRET = os.environ.get("SMS_API_KEY_SECRET", "f146bd84a6e0605bf0f7ed2bfd60d9ac")
SMS_SENDER_ID = os.environ.get("SMS_SENDER_ID", "Pywe")
SMS_GATEWAY_CONFIGURED = bool(SMS_API_BASE_URL and SMS_API_KEY_PUBLIC and SMS_API_KEY_SECRET)

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

MEDIA_URL = "/media/"
if DOCKER_ENV:
    MEDIA_ROOT = Path(os.environ.get("MEDIA_ROOT", "/app/media"))
else:
    MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# AdminUser is Django admin / staff only (AUTH_USER_MODEL). APIs authenticate
# merchants and customers via Account (MemberAuthentication + JWT).
AUTH_USER_MODEL = "core.AdminUser"
AUTHENTICATION_BACKENDS = ["pywe_cms_backend.authentication.BackendAuthentication"]

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")

_csrf = os.environ.get("CSRF_TRUSTED_ORIGINS", "")
CSRF_TRUSTED_ORIGINS = [o.strip() for o in _csrf.split(",") if o.strip()]

_cors = os.environ.get("CORS_ALLOWED_ORIGINS", "")
if _cors.strip():
    CORS_ALLOWED_ORIGINS = [o.strip() for o in _cors.split(",") if o.strip()]
elif DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
else:
    CORS_ALLOWED_ORIGINS = []

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "pywe_cms_backend.authentication.MemberAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "apis.pagination.StandardPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
    ],
}

# Manager / Account JWT: long-lived access + refresh (no silent refresh in SPA; 401 → re-login).
_access_days = int(os.environ.get("JWT_ACCESS_TOKEN_DAYS", "30"))
_refresh_days = int(os.environ.get("JWT_REFRESH_TOKEN_DAYS", "30"))

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=_access_days),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=_refresh_days),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "TOKEN_REFRESH_SERIALIZER": "apis.jwt_serializers.AccountAwareTokenRefreshSerializer",
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}
