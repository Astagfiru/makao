from datetime import date

from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from portfolio import examples, photos
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


def get_example(slug: str) -> DemoSite:
    return get_object_or_404(DemoSite, slug=slug, is_published=True)


def noindex(response: HttpResponse) -> HttpResponse:
    response["X-Robots-Tag"] = "noindex, nofollow"
    return response


def booking_context(request: HttpRequest, sandbox: examples.Sandbox) -> dict:
    feature = examples.FEATURES[sandbox.demo.theme].get("booking")
    if not feature:
        return {}
    services = sandbox.services()
    chosen = sandbox.service(request.GET.get("service", "")) or (services[0] if services else None)
    days = examples.booking_days(sandbox)
    open_days = [d for d in days if not d["off"]]
    picked = next((d for d in days if d["iso"] == request.GET.get("date") and not d["off"]), None) \
        or (open_days[0] if open_days else None)
    free = examples.slots(sandbox, picked["date"], chosen.minutes) if picked and chosen else []
    return {"booking": feature, "services": services, "chosen": chosen, "days": days, "picked": picked,
            "slots": free}


def cart_context(request: HttpRequest, sandbox: examples.Sandbox) -> dict:
    feature = examples.FEATURES[sandbox.demo.theme].get("cart")
    if not feature:
        return {}
    quantities = examples.parse_quantities(request.GET, sandbox)
    own_cup = request.GET.get("own_cup") == "on"
    pickup = examples.pickup_slots(sandbox) if examples.FEATURES[sandbox.demo.theme].get("pickup") else []
    return {"cart": feature, "items": sandbox.services(), "quantities": quantities, "own_cup": own_cup,
            "pickup_slots": pickup, "stamps": sandbox.data["stamps"],
            "stamp_marks": [i < sandbox.data["stamps"] % examples.STAMPS_FOR_GIFT for i in range(examples.STAMPS_FOR_GIFT)],
            "totals": examples.cart_total(sandbox, quantities, own_cup)}


@require_GET
def example(request: HttpRequest, slug: str) -> HttpResponse:
    site = get_example(slug)
    sandbox = examples.Sandbox(request, site)
    blocks = site.blocks or {}
    context = {
        "demo": site, "b": blocks, "features": examples.FEATURES.get(site.theme, {}),
        "hero_photo": photos.resolve(site.slug, blocks.get("hero_photo")),
        "gallery": photos.resolve_many(site.slug, blocks.get("gallery")),
        "posts": list(reversed(sandbox.data["posts"])) + examples.default_posts(site),
        **booking_context(request, sandbox), **cart_context(request, sandbox),
    }
    return noindex(render(request, f"demos/{site.theme}.html", context))


@require_POST
def book(request: HttpRequest, slug: str) -> HttpResponse:
    site = get_example(slug)
    sandbox = examples.Sandbox(request, site)
    service = sandbox.service(request.POST.get("service", ""))
    try:
        day = date.fromisoformat(request.POST.get("date", ""))
    except ValueError:
        day = None
    slot = request.POST.get("time", "")
    free = {s["time"] for s in examples.slots(sandbox, day, service.minutes) if s["free"]} if service and day else set()
    if not service or not day or slot not in free or request.POST.get("consent") != "on":
        url = reverse("portfolio:demo", args=[slug])
        query = f"?service={service.id if service else ''}&date={day.isoformat() if day else ''}&error=1#zapis"
        return redirect(url + query)
    feature = examples.FEATURES[site.theme]["booking"]
    place = request.POST.get("place", "")
    device = request.POST.get("device", "")
    number = sandbox.next_number()
    sandbox.data["bookings"].append({
        "number": number, "service": service.name, "price": service.price, "price_text": service.price_text,
        "date": day.isoformat(), "time": slot, "name": (request.POST.get("name") or "Гость").strip()[:40],
        "note": (request.POST.get("note") or "").strip()[:300], "status": statuses_for(site, "bookings")[0],
        "place": place if place in feature.get("places", []) else "",
        "device": device if device in (site.blocks or {}).get("brands", []) else "",
        "paid": False, "created": timezone.localtime().strftime("%d.%m %H:%M"),
    })
    sandbox.save()
    return redirect("portfolio:done", slug=slug, kind="bookings", number=number)


@require_POST
def order(request: HttpRequest, slug: str) -> HttpResponse:
    site = get_example(slug)
    sandbox = examples.Sandbox(request, site)
    quantities = examples.parse_quantities(request.POST, sandbox)
    own_cup = request.POST.get("own_cup") == "on"
    pickup = examples.FEATURES[site.theme].get("pickup")
    slot_ok = not pickup or request.POST.get("slot") in examples.pickup_slots(sandbox)
    if not quantities or not slot_ok or request.POST.get("consent") != "on":
        query = "&".join(f"q_{k}={v}" for k, v in quantities.items()) + ("&own_cup=on" if own_cup else "")
        return redirect(f"{reverse('portfolio:demo', args=[slug])}?{query}&error=1#zakaz")
    totals = examples.cart_total(sandbox, quantities, own_cup)
    if pickup:
        sandbox.data["stamps"] = totals["stamps"]
    first = examples.STATUSES.get(site.theme, examples.STATUSES["booking"])[0]
    number = sandbox.next_number()
    sandbox.data["orders"].append({
        "number": number, "lines": totals["lines"], "total": totals["total"], "discount": totals["discount"],
        "discounts": totals["discounts"], "own_cup": own_cup,
        "unknown": totals["unknown"], "branch": (request.POST.get("branch") or "")[:120],
        "delivery": "Навынос" if pickup else (request.POST.get("delivery") or "")[:40], "slot": (request.POST.get("slot") or "")[:20],
        "card": (request.POST.get("card_text") or "").strip()[:200], "name": (request.POST.get("name") or "Гость")[:40],
        "status": first, "paid": False, "created": timezone.localtime().strftime("%d.%m %H:%M"),
    })
    sandbox.save()
    return redirect("portfolio:done", slug=slug, kind="orders", number=number)


def find_or_404(sandbox: examples.Sandbox, kind: str, number: int) -> dict:
    if kind not in ("bookings", "orders"):
        raise Http404
    item = sandbox.find(kind, number)
    if item is None:
        raise Http404
    return item


@require_GET
def done(request: HttpRequest, slug: str, kind: str, number: int) -> HttpResponse:
    site = get_example(slug)
    sandbox = examples.Sandbox(request, site)
    item = find_or_404(sandbox, kind, number)
    can_pay = examples.FEATURES[site.theme].get("booking" if kind == "bookings" else "cart", {}).get("pay")
    amount = item.get("price") if kind == "bookings" else item.get("total")
    return noindex(render(request, "examples/done.html", {
        "demo": site, "kind": kind, "item": item, "can_pay": bool(can_pay and amount), "amount": amount,
        "statuses": statuses_for(site, kind)}))


@require_POST
def pay(request: HttpRequest, slug: str, kind: str, number: int) -> HttpResponse:
    site = get_example(slug)
    sandbox = examples.Sandbox(request, site)
    item = find_or_404(sandbox, kind, number)
    item["paid"] = True
    sandbox.save()
    return redirect("portfolio:done", slug=slug, kind=kind, number=number)


def statuses_for(site: DemoSite, kind: str) -> list[str]:
    return examples.STATUSES["booking"] if kind == "bookings" and site.theme not in examples.THEMED_BOOKINGS \
        else examples.STATUSES.get(site.theme, examples.STATUSES["booking"])


@require_GET
def track(request: HttpRequest, slug: str) -> HttpResponse:
    site = get_example(slug)
    sandbox = examples.Sandbox(request, site)
    found, kind = None, "orders"
    try:
        number = int(request.GET.get("n", ""))
    except ValueError:
        number = None
    if number:
        found = sandbox.find("orders", number)
        if found is None:
            found, kind = sandbox.find("bookings", number), "bookings"
    return noindex(render(request, "examples/track.html", {
        "demo": site, "item": found, "kind": kind, "asked": number, "statuses": statuses_for(site, kind)}))


@require_http_methods(["GET", "POST"])
def cabinet(request: HttpRequest, slug: str) -> HttpResponse:
    """Кабинет владельца (пример): заявки и статусы, цены, новости, выходные дни."""
    site = get_example(slug)
    sandbox = examples.Sandbox(request, site)
    if request.method == "POST":
        apply_cabinet_action(sandbox, request.POST)
        sandbox.save()
        return redirect(f"{reverse('portfolio:cabinet', args=[slug])}?tab={request.POST.get('tab', '')}")
    return noindex(render(request, "examples/cabinet.html", {
        "demo": site, "data": sandbox.data, "services": sandbox.services(), "features": examples.FEATURES[site.theme],
        "booking_statuses": statuses_for(site, "bookings"), "order_statuses": statuses_for(site, "orders"),
        "days": examples.booking_days(sandbox, 14), "tab": request.GET.get("tab") or "zayavki"}))


def apply_cabinet_action(sandbox: examples.Sandbox, data) -> None:
    action = data.get("action")
    if action == "status":
        kind = data.get("kind")
        if kind in ("bookings", "orders"):
            item = sandbox.find(kind, to_int(data.get("number")))
            allowed = statuses_for(sandbox.demo, kind)
            if item and data.get("status") in allowed:
                item["status"] = data["status"]
    elif action == "prices":
        for s in examples.services(sandbox.demo):
            raw = (data.get(f"p_{s.id}") or "").replace(" ", "")
            if raw.isdigit() and int(raw) < 10_000_000:
                sandbox.data["prices"][s.id] = int(raw)
            elif raw == "":
                sandbox.data["prices"].pop(s.id, None)
    elif action == "post_add":
        title = (data.get("title") or "").strip()[:120]
        if title:
            sandbox.data["posts"].append({"title": title, "text": (data.get("text") or "").strip()[:600], "own": True,
                                          "date": timezone.localdate().strftime("%d.%m.%Y")})
    elif action == "post_del":
        index = to_int(data.get("index"))
        if 0 <= index < len(sandbox.data["posts"]):
            sandbox.data["posts"].pop(index)
    elif action == "day_off":
        iso = data.get("date", "")
        days = sandbox.data["days_off"]
        if iso in days:
            days.remove(iso)
        elif len(iso) == 10:
            days.append(iso)
    elif action == "reset":
        sandbox.data.update({"bookings": [], "orders": [], "prices": {}, "posts": [], "days_off": [], "stamps": 0})


def old_demo_url(request: HttpRequest, slug: str) -> HttpResponse:
    return redirect("portfolio:demo", slug=slug, permanent=True)


def to_int(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return -1
