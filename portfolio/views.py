from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from portfolio import photos
from portfolio.models import Case, DemoSite, Niche


@require_GET
def case_list(request: HttpRequest) -> HttpResponse:
    cases = Case.published.select_related("niche", "demo")
    niches = Niche.objects.filter(cases__is_published=True).distinct()
    active = request.GET.get("niche", "")
    if active:
        cases = cases.filter(niche__slug=active)
    return render(request, "portfolio/list.html", {"cases": cases, "niches": niches, "active": active})


@require_GET
def case_detail(request: HttpRequest, slug: str) -> HttpResponse:
    case = get_object_or_404(Case.published.select_related("niche", "demo"), slug=slug)
    return render(request, "portfolio/case.html", {"case": case})


@require_GET
def demo(request: HttpRequest, slug: str) -> HttpResponse:
    site = get_object_or_404(DemoSite, slug=slug, is_published=True)
    blocks = site.blocks or {}
    context = {
        "demo": site,
        "b": blocks,
        "hero_photo": photos.resolve(site.slug, blocks.get("hero_photo")),
        "gallery": photos.resolve_many(site.slug, blocks.get("gallery")),
    }
    response = render(request, f"demos/{site.theme}.html", context)
    response["X-Robots-Tag"] = "noindex, nofollow"
    return response
