"""
Django settings for the Freelancer Finance OS backend.

See Document 2 (Technical Design / HLD-LLD) in the Zyricon folder for the
architecture this configuration implements.
"""

import sys
from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, True),
)
environ.Env.read_env(BASE_DIR / ".env")

_INSECURE_SECRET_KEY_DEFAULT = "django-insecure-dev-only-change-me"
SECRET_KEY = env("DJANGO_SECRET_KEY", default=_INSECURE_SECRET_KEY_DEFAULT)
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["127.0.0.1", "localhost"])

if not DEBUG and SECRET_KEY == _INSECURE_SECRET_KEY_DEFAULT:
    # Fail loudly at startup rather than silently running a production
    # deployment on a secret key that's sitting in this file's git history.
    raise RuntimeError(
        "DJANGO_SECRET_KEY must be set to a real secret when DJANGO_DEBUG=False. "
        "Generate one with: python -c \"from django.core.management.utils import "
        "get_random_secret_key; print(get_random_secret_key())\""
    )

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "accounts",
    "clients",
    "invoicing",
    "expenses",
    "reports",
    "integrations",
    "notifications",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

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

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
    )
}

AUTH_USER_MODEL = "accounts.User"

# `manage.py test` hashes a password for every create_user()/login() call,
# and dozens of tests do both - at the real PBKDF2 iteration count (deliberately
# slow, to resist brute force) that adds minutes to the suite for no security
# benefit in a throwaway test database. MD5 here only ever affects test runs.
if "test" in sys.argv:
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- REST Framework / JWT -------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "integrations.authentication.ApiKeyAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
    ),
    "DEFAULT_THROTTLE_RATES": {
        # Scoped throttles for the credential/enumeration-sensitive endpoints
        # (see accounts/views.py) - everything else is deliberately
        # unthrottled for now, since a blanket global throttle would need
        # tuning against real usage patterns this project doesn't have yet.
        "login": "10/min",
        "register": "5/hour",
        "password_reset": "5/hour",
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    # Without this, a refresh token that's already been rotated (used once)
    # can still be replayed to mint new access tokens - it's only "rotated",
    # not actually invalidated, until it's on the blacklist too.
    "BLACKLIST_AFTER_ROTATION": True,
}

# --- CORS ------------------------------------------------------------------

CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS", default=["http://localhost:5173"]
)

# --- Email -------------------------------------------------------------

EMAIL_BACKEND = env(
    "EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend"
)
DEFAULT_FROM_EMAIL = env(
    "DEFAULT_FROM_EMAIL", default="no-reply@freelancerfinanceos.local"
)

# --- Razorpay ------------------------------------------------------------

RAZORPAY_KEY_ID = env("RAZORPAY_KEY_ID", default="")
RAZORPAY_KEY_SECRET = env("RAZORPAY_KEY_SECRET", default="")
RAZORPAY_WEBHOOK_SECRET = env("RAZORPAY_WEBHOOK_SECRET", default="")

# Frontend base URL, used when building links inside emails.
FRONTEND_BASE_URL = env("FRONTEND_BASE_URL", default="http://localhost:5173")

# --- Production security headers -------------------------------------------
# Only applied when DEBUG=False, since most of these break local HTTP dev
# (e.g. SECURE_SSL_REDIRECT would redirect-loop plain http://127.0.0.1:8000).
# SECURE_PROXY_SSL_HEADER is commented out because it must match whatever
# your specific host's reverse proxy actually sends - setting it to trust the
# wrong header on the wrong platform lets an attacker spoof "this is HTTPS"
# over plain HTTP. Uncomment and confirm the header name with your host
# (Render/Railway both use X-Forwarded-Proto) before deploying.
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30  # 30 days - start low, raise once confident
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = False
    # SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
