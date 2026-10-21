from django import template

register = template.Library()


@register.filter
def rub(value) -> str:
    """15000 -> «15 000 ₽» (узкий неразрывный пробел между разрядами)."""
    try:
        number = int(value)
    except (TypeError, ValueError):
        return ""
    return f"{number:,}".replace(",", " ") + " ₽"
