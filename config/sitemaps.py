from django.conf import settings
from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from core.content import SEO_PAGES
from portfolio.models import Case

PROTOCOL = "https" if settings.SITE_URL.startswith("https://") else "http"


class StaticPagesSitemap(Sitemap):
    protocol = PROTOCOL

    def items(self) -> list[str]:
        return ["core:home", "portfolio:list", "core:contacts", *(f"core:seo-{slug}" for slug in SEO_PAGES),
                "core:policy", "core:consent"]

    def location(self, item: str) -> str:
        return reverse(item)

    def priority(self, item: str) -> float:
        return 1.0 if item == "core:home" else 0.3 if item in ("core:policy", "core:consent") else 0.8


class CaseSitemap(Sitemap):
    protocol = PROTOCOL
    priority = 0.6

    def items(self):
        return Case.published.all()


# Демо-сайты в sitemap не попадают: это концепты чужих бизнесов, у них noindex.
SITEMAPS = {"pages": StaticPagesSitemap, "cases": CaseSitemap}
