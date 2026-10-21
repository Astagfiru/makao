"""Проверка: в боевом режиме у админа не должен остаться пароль по умолчанию."""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.db import DatabaseError


def admins_with_default_password() -> list[str]:
    """Логины активных суперпользователей, у которых пароль всё ещё «admin»."""
    user_model = get_user_model()
    try:
        admins = list(user_model.objects.filter(is_superuser=True, is_active=True))
    except DatabaseError:  # база ещё не создана (до первой миграции)
        return []
    return [user.get_username() for user in admins if user.check_password(settings.DEFAULT_ADMIN_PASSWORD)]


def default_password_message(usernames: list[str]) -> str:
    names = ", ".join(usernames)
    return (f"DEBUG=False, а у админа ({names}) пароль по умолчанию. Сайт не запущен. "
            f"Смените пароль: python manage.py changepassword {usernames[0]}")


def assert_admin_password_changed() -> None:
    """Вызывается при старте сервера (wsgi.py): отказ запуска со стандартным паролем."""
    if settings.DEBUG:
        return
    weak = admins_with_default_password()
    if weak:
        raise ImproperlyConfigured(default_password_message(weak))
