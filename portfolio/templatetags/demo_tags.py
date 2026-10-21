from django import template

from portfolio import photos

register = template.Library()

DAY_NAMES = [("mon", "Пн"), ("tue", "Вт"), ("wed", "Ср"), ("thu", "Чт"), ("fri", "Пт"), ("sat", "Сб"), ("sun", "Вс")]


@register.filter
def demo_photo(item: dict | None, slug: str):
    """Фото из блоков демо: файл из media, иначе сток, иначе None (шаблон рисует заглушку)."""
    return photos.resolve(slug, item)


@register.filter
def demo_photos(items: list | None, slug: str) -> list:
    return photos.resolve_many(slug, items)


@register.filter
def hours_rows(hours: dict | None) -> list[tuple[str, str]]:
    """{"mon": "10:00–19:00", ...} -> [("Пн–Пт", "10:00–19:00"), ("Вс", "выходной")] с группировкой подряд идущих дней."""
    if not hours:
        return []
    rows: list[list] = []
    for key, label in DAY_NAMES:
        value = hours.get(key) or "выходной"
        if rows and rows[-1][2] == value:
            rows[-1][1] = label
        else:
            rows.append([label, label, value])
    return [(first if first == last else f"{first}–{last}", value) for first, last, value in rows]


@register.filter
def open_daily(hours: dict | None) -> bool:
    return bool(hours) and len({hours.get(key) for key, _ in DAY_NAMES}) == 1 and bool(hours.get("mon"))


@register.filter
def price_groups(prices: list | None) -> list[tuple[str, list]]:
    """Позиции прайса, сгруппированные по категориям в исходном порядке; «ПУХОВИКИ (...)» -> «Пуховики (...)»."""
    groups: dict[str, list] = {}
    for item in prices or []:
        name = (item.get("category") or "Услуги").strip()
        if name.isupper() or name.split(" (")[0].isupper():
            name = name[:1] + name[1:].lower()
        name = name[:1].upper() + name[1:]
        groups.setdefault(name, []).append(item)
    return list(groups.items())


@register.filter
def comma(value) -> str:
    """Рейтинг: 4.9 -> «4,9», 5 -> «5,0»."""
    try:
        return f"{float(value):.1f}".replace(".", ",")
    except (TypeError, ValueError):
        return ""
