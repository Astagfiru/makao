from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand

from core.seed import seed_core
from portfolio.seed import copy_demo_photos, seed_portfolio


class Command(BaseCommand):
    help = "Подготовить сайт: миграции, админ из .env, стартовый контент и демо-сайты, фото демо."
    requires_system_checks = []  # команда сама чинит базу и пароль, проверки ей не мешают

    def add_arguments(self, parser) -> None:
        parser.add_argument("--refresh-demos", action="store_true",
                            help="Перезаписать демо-сайты и кейсы данными из docs/research и portfolio/demos.")
        parser.add_argument("--reset-admin-password", action="store_true",
                            help="Выставить админу пароль из ADMIN_PASSWORD в .env.")

    def handle(self, *args, **options) -> None:
        call_command("migrate", interactive=False, verbosity=0)
        self.stdout.write(self.style.SUCCESS("1/4 База данных готова (миграции применены)."))

        self.stdout.write(self.style.SUCCESS(f"2/4 {self.ensure_admin(options['reset_admin_password'])}"))

        counts = {**seed_core(), **seed_portfolio(refresh=options["refresh_demos"])}
        added = ", ".join(f"{name}: {n}" for name, n in counts.items()) or "ничего — всё уже было"
        self.stdout.write(self.style.SUCCESS(f"3/4 Контент: добавлено {added}."))

        copied, missing = copy_demo_photos()
        note = f"скопировано {copied}" + (f"; нет папки фото у {', '.join(missing)} — будут сток/заглушки"
                                          if missing else "")
        self.stdout.write(self.style.SUCCESS(f"4/4 Фото демо-сайтов: {note}."))

        if settings.ADMIN_PASSWORD == settings.DEFAULT_ADMIN_PASSWORD:
            self.stdout.write(self.style.WARNING(
                "ВНИМАНИЕ: пароль админки стандартный (admin). Перед запуском в интернете смените его!"))
        self.stdout.write("Готово. Запуск: .venv/Scripts/python.exe manage.py runserver 3000 → http://localhost:3000")

    def ensure_admin(self, reset_password: bool) -> str:
        user_model = get_user_model()
        username = settings.ADMIN_USERNAME
        user = user_model.objects.filter(username=username).first()
        if user is None:
            user_model.objects.create_superuser(username, settings.ADMIN_EMAIL, settings.ADMIN_PASSWORD)
            return f"Админ «{username}» создан (логин и пароль — из .env)."
        if reset_password:
            user.set_password(settings.ADMIN_PASSWORD)
            user.is_active = user.is_staff = user.is_superuser = True
            user.save()
            return f"Админу «{username}» выставлен пароль из .env."
        return f"Админ «{username}» уже есть — пароль не трогаю (сбросить: --reset-admin-password)."
