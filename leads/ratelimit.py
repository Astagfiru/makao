"""Ограничение частоты заявок с одного адреса. Адрес хранится только в памяти и только в виде хэша."""
import hashlib

from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest


def client_ip(request: HttpRequest) -> str:
    if settings.BEHIND_PROXY:  # за Caddy настоящий адрес посетителя — в X-Forwarded-For
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded:
            return forwarded.split(",")[-1].strip()
    return request.META.get("REMOTE_ADDR", "")


def _key(request: HttpRequest) -> str:
    digest = hashlib.sha256((settings.SECRET_KEY + client_ip(request)).encode()).hexdigest()[:32]
    return f"lead-rate:{digest}"


def is_limited(request: HttpRequest) -> bool:
    return cache.get(_key(request), 0) >= settings.LEAD_RATE_LIMIT


def register_attempt(request: HttpRequest) -> None:
    key = _key(request)
    if cache.add(key, 1, timeout=settings.LEAD_RATE_WINDOW):
        return
    try:
        cache.incr(key)
    except ValueError:  # ключ успел истечь между add и incr
        cache.add(key, 1, timeout=settings.LEAD_RATE_WINDOW)
