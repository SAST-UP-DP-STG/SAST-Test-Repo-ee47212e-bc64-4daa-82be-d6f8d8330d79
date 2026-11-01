import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "clinic-scheduling-dev-secret-key")
DEBUG = os.environ.get("DEBUG", "true").lower() == "true"
ALLOWED_HOSTS = ["*"]

SHARED_JWT_SECRET = os.environ.get("SHARED_JWT_SECRET", "clinic-scheduling-shared-jwt-secret")
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_TTL_MINUTES = int(os.environ.get("JWT_TTL_MINUTES", "480"))

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "guardian",
    "rules.apps.AutodiscoverRulesConfig",
    "scheduling",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
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

WSGI_APPLICATION = "core.wsgi.application"
ASGI_APPLICATION = "core.asgi.application"

DATABASE_PATH = os.environ.get("DATABASE_PATH", "data/clinic.db")
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / DATABASE_PATH,
    }
}

AUTH_USER_MODEL = "scheduling.User"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "guardian.backends.ObjectPermissionBackend",
]

ANONYMOUS_USER_NAME = None

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "scheduling.auth.SharedJWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]

LOGIN_URL = "/login"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SESSION_COOKIE_NAME = "clinic_session"
