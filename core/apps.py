from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "Сайт: контент и настройки"

    def ready(self) -> None:
        from core import checks  # noqa: F401 — регистрирует проверку пароля админки
