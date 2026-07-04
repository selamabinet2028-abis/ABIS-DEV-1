"""ABIS base settings — shared by dev/test/prod.

Everything environment-specific is read from env vars (django-environ),
with dev-safe defaults. See backend/.env.example.
"""

from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # backend/

env = environ.Env()
_env_file = BASE_DIR / ".env"
if _env_file.exists():
    environ.Env.read_env(_env_file)

SECRET_KEY = env("DJANGO_SECRET_KEY", default="django-insecure-abis-dev-only")
DEBUG = False
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

# ---------------------------------------------------------------- apps
DJANGO_APPS = [
    "daphne",  # must precede staticfiles: ASGI runserver
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",  # GIN indexes (Person.addresses)
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    "django_filters",
    "corsheaders",
    "channels",
]

LOCAL_APPS = [
    "apps.accounts",
    "apps.basedata",
    "apps.registration",
    "apps.enrollment",
    "apps.payments",
    "apps.notifications",
    "apps.preprocessing",
    "apps.matching",
    "apps.pis",
    "apps.investigation",
    "apps.clearance",
    "apps.verification",
    "apps.audit",
    "apps.apimgmt",
    "apps.watchlist",
    "apps.appointments",
    "apps.devices",
    "apps.documents",
    "apps.reports",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.audit.middleware.AuditContextMiddleware",  # after auth: needs request.user
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

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

# ---------------------------------------------------------------- database
DATABASES = {
    # Default matches docker-compose.yml (host port 5433 — 5432 is often taken).
    "default": env.db_url(
        "DATABASE_URL", default="postgres://abis:abis@localhost:5433/abis"
    ),
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------- auth
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 10},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------- DRF / API
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    # RBAC golden rule: deny by default. Public endpoints opt in via AllowAny.
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "config.pagination.StandardPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/min",
        "user": "600/min",
        "auth": "10/min",  # login attempts (ScopedRateThrottle on LoginView)
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "ABIS API",
    "DESCRIPTION": "Automated Biometric Identification System — REST API v1",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": r"/api/v1",
    # Distinct names for same-named choice sets across apps.
    "ENUM_NAME_OVERRIDES": {
        "BiometricModalityEnum": "apps.enrollment.models.Modality.choices",
        "LatentModalityEnum": "apps.investigation.models.LATENT_MODALITY_CHOICES",
        "MatchJobTypeEnum": "apps.matching.models.MATCH_JOB_TYPE_CHOICES",
        "LatentSearchJobTypeEnum": "apps.investigation.serializers.LATENT_SEARCH_JOB_TYPES",
    },
}

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
CORS_ALLOW_CREDENTIALS = True  # refresh cookie (ADR-006/ADR-013)

# Insert-only audit trail (golden rule #4). Feature tasks append their
# person/biometric models here as they land (T-006+).
ABIS_AUDITED_MODELS = [
    "accounts.User",
    "accounts.Role",
    "basedata.OrgUnit",
    "basedata.Person",
    "basedata.LookupValue",
    "basedata.InvestigationCategory",
    "appointments.Station",
    "enrollment.Enrollment",
    "enrollment.BiometricRecord",
    "enrollment.BiometricTemplate",
    "matching.MatchJob",
    "matching.MatchCandidate",
    "investigation.Case",
    "investigation.LatentPrint",
    "investigation.EvidenceDocument",
    "pis.PhotoProbe",
    "watchlist.Watchlist",
    "watchlist.WatchlistEntry",
    "watchlist.WatchlistAlert",
]
ABIS_AUDIT_MASK_FIELDS = {"password", "template_bytes"}
ABIS_AUDIT_IGNORE_FIELDS = {"last_login", "updated_at"}

# Upload validation (security golden rule)
ABIS_MAX_UPLOAD_MB = env.int("ABIS_MAX_UPLOAD_MB", default=5)

# Biometric template encryption (ADR-008) + NFIQ-like acceptance threshold
ABIS_FIELD_KEY = env(
    "ABIS_FIELD_KEY",
    default="neP8RPJf4BdE388S-9W5FDvEw0bA6fGfS6nkjG0atJY=",  # dev-only key
)
ABIS_QUALITY_THRESHOLD = env.int("ABIS_QUALITY_THRESHOLD", default=2)

# Matching engine adapter (ADR-004): swap for the vendor SDK engine in prod.
MATCHING_ENGINE = env(
    "MATCHING_ENGINE", default="apps.matching.engines.mock.MockEngine"
)
ABIS_MATCH_THRESHOLD = env.float("ABIS_MATCH_THRESHOLD", default=80.0)
ABIS_MATCH_TOP_K = env.int("ABIS_MATCH_TOP_K", default=20)

# Account lockout + refresh-cookie policy (ADR-013)
ABIS_AUTH = {
    "LOCKOUT_THRESHOLD": env.int("ABIS_LOCKOUT_THRESHOLD", default=5),
    "LOCKOUT_MINUTES": env.int("ABIS_LOCKOUT_MINUTES", default=15),
    "REFRESH_COOKIE_NAME": "abis_refresh",
    "REFRESH_COOKIE_PATH": "/api/v1/auth/",
    "REFRESH_COOKIE_SAMESITE": "Lax",
}

# ---------------------------------------------------------------- celery / channels
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://localhost:6379/1")
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = "Africa/Addis_Ababa"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [env("CHANNELS_REDIS_URL", default="redis://localhost:6379/2")],
        },
    },
}

# ---------------------------------------------------------------- i18n / static / media
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Addis_Ababa"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# ---------------------------------------------------------------- logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "{levelname} {asctime} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "standard"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django.request": {"level": "WARNING"},
    },
}
