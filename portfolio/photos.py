"""Фото демо-сайтов.

Фото бизнесов из 2ГИС не лежат в публичном репозитории: `manage.py setup` копирует их из
research-private/<slug>/photos/ в media/demos/<slug>/. Нет файла — берём сток из static/demos/stock/,
нет и стока — шаблон рисует нейтральную заглушку.
"""
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings
from django.templatetags.static import static


@dataclass(frozen=True)
class Photo:
    url: str
    alt: str
    source: str  # "2gis" или "stock"
    width: int | None = None
    height: int | None = None


def resolve(slug: str, item: dict | None) -> Photo | None:
    """item из блоков демо: {"file": "hero.webp", "stock": "demos/stock/<slug>/x.webp", "alt": "..."}."""
    if not item:
        return None
    size = (item.get("w"), item.get("h"))
    file = item.get("file")
    if file and (Path(settings.MEDIA_ROOT) / "demos" / slug / file).is_file():
        return Photo(f"{settings.MEDIA_URL}demos/{slug}/{file}", item.get("alt", ""), "2gis", *size)
    stock = item.get("stock")
    if stock:
        return Photo(static(stock), item.get("alt", ""), "stock", *item.get("stock_size", (None, None)))
    return None


def resolve_many(slug: str, items: list[dict] | None) -> list[Photo]:
    return [photo for photo in (resolve(slug, item) for item in items or []) if photo]
