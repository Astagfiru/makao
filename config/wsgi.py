"""Точка входа для gunicorn на сервере."""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_wsgi_application()

from core.security import assert_admin_password_changed  # noqa: E402 — нужен загруженный Django

assert_admin_password_changed()  # DEBUG=False и пароль админа «admin» — сервер не стартует
