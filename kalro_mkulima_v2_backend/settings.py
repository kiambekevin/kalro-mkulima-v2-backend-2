# kalro_mkulima_v2_backend/settings.py
import os
from datetime import timedelta
from pathlib import Path
from celery.schedules import crontab

import environ

# ───────────────────────────── Paths ─────────────────────────────

BASE_DIR = Path(__file__).resolve().parent.parent

# ───────────────────────────── Env ─────────────────────────────
env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    DJANGO_CSRF_TRUSTED_ORIGINS=(list, []),
    USE_S3=(bool, False),
    JWT_ACCESS_LIFETIME_MINUTES=(int, 30),
    JWT_REFRESH_LIFETIME_DAYS=(int, 30),
    KALRO_BADGE_EXPIRY_DAYS=(int, 0),
    KALRO_MAX_OFFLINE_DOWNLOAD_MB=(int, 200),
    KALRO_DEFAULT_HLS_VARIANT_HEIGHT=(int, 480),
    STREAM_SIGNING_TTL_SECONDS=(int, 600),
    AWS_QUERYSTRING_EXPIRE=(int, 3600),
    CELERY_TASK_ALWAYS_EAGER=(bool, False),
)

# Read `.env` at the project root if it exists
environ.Env.read_env(os.path.join(BASE_DIR, ".env"))

# ───────────────────────────── Core ─────────────────────────────

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env("DJANGO_CSRF_TRUSTED_ORIGINS")

# ───────────────────────────── Apps ─────────────────────────────

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    "storages",
    "django_celery_beat",
    "django_celery_results",
    "phonenumber_field",
    "django_extensions",
]

LOCAL_APPS = [
    "apps.common",
    "apps.accounts",
    "apps.counties",
    "apps.courses",
    "apps.progress",
    "apps.badges",
    "apps.fielddays",
    "apps.dashboard",
    # "apps.notifications",
    "apps.media",
    "apps.analytics",
    "api",
    # "apps.reports",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ───────────────────────────── Middleware ─────────────────────────────
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
    # Custom
    "apps.accounts.middleware.LastSeenMiddleware",
]

ROOT_URLCONF = "kalro_mkulima_v2_backend.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
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

WSGI_APPLICATION = "kalro_mkulima_v2_backend.wsgi.application"
ASGI_APPLICATION = "kalro_mkulima_v2_backend.asgi.application"

# ───────────────────────────── Database ─────────────────────────────
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",  # Updated backend
        "NAME": env("POSTGRES_DB", default="kalro"),
        "USER": env("POSTGRES_USER", default="kalro"),
        "PASSWORD": env("POSTGRES_PASSWORD", default=""),
        "HOST": env("POSTGRES_HOST", default="localhost"),
        "PORT": env("POSTGRES_PORT", default="5432"),
        "CONN_MAX_AGE": 600,  # Keeps connections persistent for 10 min
        "CONN_HEALTH_CHECKS": True,
        "ATOMIC_REQUESTS": True,
    }
}

# ───────────────────────────── Auth ─────────────────────────────

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ───────────────────────────── DRF ─────────────────────────────

REST_FRAMEWORK = {
    # Auth
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ),

    # Versioning
    "DEFAULT_VERSIONING_CLASS": "api.versioning.DefaultVersioning",
    "DEFAULT_VERSION": "v1",
    "ALLOWED_VERSIONS": ("v1", "v2"),

    # Parsing & rendering
    "DEFAULT_PARSER_CLASSES": (
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ),
    "DEFAULT_RENDERER_CLASSES": (
        ("rest_framework.renderers.JSONRenderer",)
        + (("rest_framework.renderers.BrowsableAPIRenderer",) if DEBUG else ())
    ),

    # Pagination
    "DEFAULT_PAGINATION_CLASS": "api.pagination.DefaultPagination",
    "PAGE_SIZE": 20,

    # Filtering
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),

    # Throttling
    "DEFAULT_THROTTLE_CLASSES": (
        "api.throttling.AnonBurstThrottle",
        "api.throttling.UserSustainedThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/min",
        "user": "600/min",
        "auth": "10/min",
        "verify": "60/min",
        "upload": "10/hour",
    },

    # Errors + schema
    "EXCEPTION_HANDLER": "api.exceptions.exception_handler",
    "DEFAULT_SCHEMA_CLASS": "api.schema.KalroAutoSchema",
}

# ───────────────────────────── JWT ─────────────────────────────

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=env.int("JWT_ACCESS_LIFETIME_MINUTES", default=30),
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=env.int("JWT_REFRESH_LIFETIME_DAYS", default=30),
    ),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# ───────────────────────────── OpenAPI ─────────────────────────────

# The full SPECTACULAR_SETTINGS lives in `api/schema.py` so it can
# reference classes and include per-tag descriptions. Import it here
# so Django settings stay the single source of truth.
try:
    from api.schema import SPECTACULAR_SETTINGS  # noqa: F401
except Exception:  # noqa: BLE001
    # Fallback — the api package may not be importable yet (e.g. during
    # the very first migration). Keep a minimal config so the app boots.
    SPECTACULAR_SETTINGS = {
        "TITLE": "KALRO Mkulima API",
        "DESCRIPTION": "Free online and offline agricultural training for Kenya.",
        "VERSION": "1.0.0",
        "SERVE_INCLUDE_SCHEMA": False,
    }

# ───────────────────────────── CORS ─────────────────────────────
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5175",
    "http://127.0.0.1:5175",
]

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = (
    "accept",
    "authorization",
    "content-type",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
    "x-kalro-client",   # used by the Service Worker for offline media
)

# ───────────────────────────── Celery ─────────────────────────────

CELERY_BROKER_URL = env("CELERY_BROKER_URL", default=env("REDIS_URL", default="redis://localhost:6379/0"))
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default=CELERY_BROKER_URL)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "Africa/Nairobi"
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=False)

CELERY_BEAT_SCHEDULE = {
    "analytics-build-daily-rollup": {
        "task": "apps.analytics.tasks.build_daily_rollup",
        "schedule": crontab(hour=2, minute=0),
    },
    "analytics-prune-old-events": {
        "task": "apps.analytics.tasks.prune_old_visit_events",
        "schedule": crontab(day_of_month=1, hour=3, minute=0),
    },
}
# ───────────────────────────── Cache ─────────────────────────────

# CACHES = {
#     "default": {
#         "BACKEND": "django_redis.cache.RedisCache",
#         "LOCATION": env("CACHE_URL", default=env("REDIS_URL", default="redis://localhost:6379/1")),
#         "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
#     },
# }

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "django_cache_table",
    }
}

# ───────────────────────────── Static & media ─────────────────────────────

STATIC_URL = "/django-static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

USE_S3 = env.bool("USE_S3", default=False)

if USE_S3:
    AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default="")
    AWS_S3_ENDPOINT_URL = env("AWS_S3_ENDPOINT_URL", default="")
    AWS_S3_CUSTOM_DOMAIN = env("AWS_S3_CUSTOM_DOMAIN", default="")
    AWS_QUERYSTRING_AUTH = env.bool("AWS_QUERYSTRING_AUTH", default=True)
    AWS_QUERYSTRING_EXPIRE = env.int("AWS_QUERYSTRING_EXPIRE", default=3600)

    STORAGES = {
        "default": {"BACKEND": "storages.backends.s3.S3Storage"},
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
    }
else:
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
    }

# ───────────────────────────── Email ─────────────────────────────

EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@kalro.org")
SERVER_EMAIL = env("SERVER_EMAIL", default="noreply@kalro.org")

# ───────────────────────────── i18n ─────────────────────────────

LANGUAGE_CODE = "en-us"
LANGUAGES = [("en", "English"), ("sw", "Kiswahili")]
TIME_ZONE = "Africa/Nairobi"
USE_I18N = True
USE_TZ = True

# ───────────────────────────── Defaults ─────────────────────────────

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ───────────────────────────── KALRO-specific ─────────────────────────────

KALRO_BADGE_ID_PREFIX = env("KALRO_BADGE_ID_PREFIX", default="KALRO-B")
KALRO_BADGE_EXPIRY_DAYS = env.int("KALRO_BADGE_EXPIRY_DAYS", default=0)
KALRO_BADGE_VERIFY_BASE_URL = env(
    "KALRO_BADGE_VERIFY_BASE_URL",
    default="http://localhost:5173/badges/verify",
)

KALRO_MAX_OFFLINE_DOWNLOAD_MB = env.int("KALRO_MAX_OFFLINE_DOWNLOAD_MB", default=200)
KALRO_DEFAULT_HLS_VARIANT_HEIGHT = env.int("KALRO_DEFAULT_HLS_VARIANT_HEIGHT", default=480)

# Media signing (HMAC for signed video/PDF URLs)
MEDIA_SIGNING_KEY = env("MEDIA_SIGNING_KEY", default=SECRET_KEY)

# Video streaming
STREAM_BASE_URL = env("STREAM_BASE_URL", default="")
STREAM_SIGNING_KEY = env("STREAM_SIGNING_KEY", default="")
STREAM_SIGNING_TTL_SECONDS = env.int("STREAM_SIGNING_TTL_SECONDS", default=600)

# ───────────────────────────── Security (production only) ─────────────────────────────

if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    X_FRAME_OPTIONS = "DENY"

# ───────────────────────────── Logging ─────────────────────────────

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "[{levelname}] {asctime} {name}: {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django.request": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "kalro.request": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}