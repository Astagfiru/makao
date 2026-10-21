"""Уведомление о заявке в Telegram — БЕЗ персональных данных.

Telegram — зарубежный сервис, передача туда имени и телефона была бы трансграничной передачей ПДн.
Поэтому в сообщении только номер заявки и ссылка на неё в админке.
"""
import logging
import threading
from functools import partial
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.db import transaction
from django.urls import reverse

logger = logging.getLogger("leads")
TIMEOUT_SECONDS = 5


def build_message(lead_id: int) -> str:
    link = settings.SITE_URL + reverse("admin:leads_lead_change", args=[lead_id])
    return f"Новая заявка №{lead_id}\n{link}"


def send_telegram(text: str) -> bool:
    """Отправить текст в чат. Нет токена или chat_id — тихо пропускаем."""
    token, chat_id = settings.TELEGRAM_BOT_TOKEN, settings.TELEGRAM_CHAT_ID
    if not token or not chat_id:
        return False
    data = urlencode({"chat_id": chat_id, "text": text, "disable_web_page_preview": "true"}).encode()
    request = Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data)
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:  # noqa: S310 — адрес фиксированный
            return response.status == 200
    except (URLError, TimeoutError, OSError) as exc:  # токен в лог не пишем
        logger.warning("Telegram: уведомление не отправлено (%s)", exc.__class__.__name__)
        return False


def start_background(text: str) -> None:
    threading.Thread(target=send_telegram, args=(text,), daemon=True).start()


def notify_new_lead(lead_id: int) -> None:
    """После сохранения заявки в БД — отправить уведомление в фоне, не задерживая посетителя."""
    if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID:
        transaction.on_commit(partial(start_background, build_message(lead_id)))
