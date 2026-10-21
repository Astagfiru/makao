from django.conf import settings
from django.http import HttpRequest
from django.utils.functional import SimpleLazyObject

from core.models import ContactChannel, SiteSettings


def _channels() -> list[ContactChannel]:
    return list(ContactChannel.objects.filter(is_active=True))


def site(request: HttpRequest) -> dict:
    """Реквизиты и каналы связи для шапки, футера и блоков CTA (запросы к БД — только если нужны)."""
    channels = SimpleLazyObject(_channels)
    return {
        "site_settings": SimpleLazyObject(SiteSettings.load),
        "channels_header": SimpleLazyObject(lambda: [c for c in channels if c.show_in_header]),
        "channels_footer": SimpleLazyObject(lambda: [c for c in channels if c.show_in_footer]),
        "channels_cta": SimpleLazyObject(lambda: [c for c in channels if c.show_in_cta]),
        "SITE_URL": settings.SITE_URL,
    }
