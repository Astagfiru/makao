"""Настройки сайта. Всё, что меняется между компьютером и сервером, читается из файла .env."""
import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DEFAULT_ADMIN_PASSWORD = "admin"
DEV_SECRET_KEY = "dev-only-insecure-key-change-me"


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on", "да"}


def env_list(name: str, default: str = "") -> list[str]:
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


DEBUG = env_bool("DEBUG", False)

SECRET_KEY = os.getenv("SECRET_KEY", "").strip() or (DEV_SECRET_KEY if DEBUG else "")
if not SECRET_KEY:
    raise ImproperlyConfigured("Задайте SECRET_KEY в файле .env (при DEBUG=False он обязателен).")

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin").strip() or "admin"
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", DEFAULT_ADMIN_PASSWORD)
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "").strip()

# Боевой режим со стандартным паролем админки — отказ запуска (проверка БД — в core/checks.py и wsgi.py).
if not DEBUG and ADMIN_PASSWORD == DEFAULT_ADMIN_PASSWORD:
    raise ImproperlyConfigured(
        "DEBUG=False, а пароль админки стандартный (admin). Задайте свой ADMIN_PASSWORD в .env "
        "и смените пароль: python manage.py changepassword " + ADMIN_USERNAME
    )

SITE_URL = os.getenv("SITE_URL", "http://localhost:3000").strip().rstrip("/")
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

# Отдавать /media/ самим Django (на сервере это делает Caddy). Для локального запуска с DEBUG=False.
SERVE_MEDIA = env_bool("SERVE_MEDIA", DEBUG)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
    "core",
    "portfolio",
    "leads",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.SecurityHeadersMiddleware",
]

ROOT_URLCONF = "config.urls"

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
                "core.context_processors.site",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": Path(os.getenv("DB_PATH", "") or BASE_DIR / "db.sqlite3"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "ru"
LANGUAGES = [("ru", "Русский")]
TIME_ZONE = "Asia/Yakutsk"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        if DEBUG
        else "whitenoise.storage.CompressedManifestStaticFilesStorage"
    },
}
WHITENOISE_MAX_AGE = 31536000 if not DEBUG else 0

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Безопасность: cookie недоступны из JS, на сервере — только по HTTPS.
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"
DATA_UPLOAD_MAX_MEMORY_SIZE = 6 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 6 * 1024 * 1024

if not DEBUG:
    SESSION_COOKIE_SECURE = env_bool("COOKIE_SECURE", True)
    CSRF_COOKIE_SECURE = env_bool("COOKIE_SECURE", True)
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_HSTS_SECONDS = int(os.getenv("HSTS_SECONDS", "31536000"))
    SECURE_SSL_REDIRECT = env_bool("SSL_REDIRECT", False)  # редирект на HTTPS делает Caddy

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "makao"}}

# Заявки: не больше LEAD_RATE_LIMIT штук за LEAD_RATE_WINDOW секунд с одного адреса (адрес в БД не пишем).
LEAD_RATE_LIMIT = int(os.getenv("LEAD_RATE_LIMIT", "5"))
LEAD_RATE_WINDOW = int(os.getenv("LEAD_RATE_WINDOW", "600"))
# Сайт за Caddy: адрес посетителя берём из X-Forwarded-For (Caddy подставляет его сам).
BEHIND_PROXY = env_bool("BEHIND_PROXY", False)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {
        "leads": {"handlers": ["console"], "level": "INFO"},
        "core": {"handlers": ["console"], "level": "INFO"},
    },
}
