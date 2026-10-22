from django.conf import settings
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from django.utils import timezone

from core.content import ADVANTAGES, SEO_PAGES, STEPS
from core.models import FAQItem, Review, Tariff
from leads.forms import LeadForm
from portfolio.models import Case


def lead_form(page: str) -> LeadForm:
    return LeadForm(initial={"page": page})


def tariffs_with_launch() -> list[Tariff]:
    """Тарифы с датой готовности, если начать сегодня (по времени Якутска)."""
    today = timezone.localdate()
    tariffs = list(Tariff.objects.filter(is_active=True))
    for tariff in tariffs:
        tariff.launch_from, tariff.launch_to = tariff.launch_window(today)
    return tariffs


@require_GET
def home(request: HttpRequest) -> HttpResponse:
    context = {
        "tariffs": tariffs_with_launch(),
        "advantages": ADVANTAGES,
        "steps": STEPS,
        "reviews": Review.published.all(),
        "faq": FAQItem.objects.filter(is_published=True),
        "cases": Case.published.select_related("niche", "demo")[:9],
        "form": lead_form("/"),
    }
    return render(request, "core/home.html", context)


@require_GET
def contacts(request: HttpRequest) -> HttpResponse:
    return render(request, "core/contacts.html", {"form": lead_form("/contacts/")})


@require_GET
def seo_page(request: HttpRequest, slug: str) -> HttpResponse:
    page = SEO_PAGES.get(slug)
    if page is None:
        raise Http404
    context = {
        "page": page,
        "slug": slug,
        "tariffs": tariffs_with_launch(),
        "cases": Case.published.select_related("niche", "demo")[:3],
        "form": lead_form(f"/{slug}/"),
    }
    return render(request, "core/seo_page.html", context)


@require_GET
def policy(request: HttpRequest) -> HttpResponse:
    return render(request, "core/policy.html")


@require_GET
def consent(request: HttpRequest) -> HttpResponse:
    return render(request, "core/consent.html")


@require_GET
def robots_txt(request: HttpRequest) -> HttpResponse:
    site_url = settings.SITE_URL
    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        "Disallow: /zayavka/",
        "Disallow: /spasibo/",
        "",
        f"Sitemap: {site_url}/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain; charset=utf-8")


def page_not_found(request: HttpRequest, exception: Exception) -> HttpResponse:
    return render(request, "404.html", status=404)
