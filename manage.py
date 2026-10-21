#!/usr/bin/env python
"""Командная строка Django: python manage.py <команда>."""
import os
import secrets
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def ensure_env_file() -> None:
    """Первый запуск на своём компьютере: создать .env из .env.example со случайным SECRET_KEY."""
    env_file, example = BASE_DIR / ".env", BASE_DIR / ".env.example"
    if env_file.exists() or not example.exists():
        return
    text = example.read_text(encoding="utf-8").replace("SECRET_KEY=", f"SECRET_KEY={secrets.token_urlsafe(50)}", 1)
    env_file.write_text(text, encoding="utf-8")
    print("Создан файл .env из .env.example (для работы на своём компьютере).")


def main() -> None:
    ensure_env_file()
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
