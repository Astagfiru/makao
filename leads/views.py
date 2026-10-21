from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from core.models import SiteSettings
from leads import ratelimit
from leads.forms import LeadForm
from leads.models import Lead
from leads.telegram import notify_new_lead

SESSION_KEY = "last_lead_id"


def save_lead(data: dict) -> Lead:
    """Сохранить заявку вместе с фактом согласия: дата/время и версии документов на этот момент."""
    site = SiteSettings.load()
    return Lead.objects.create(
        name=data["name"], phone=data["phone"], message=data.get("message", ""), page=data.get("page", ""),
        consent=True, consent_at=timezone.now(),
        policy_version=site.policy_version, consent_version=site.consent_version,
    )


@require_http_methods(["GET", "POST"])
def lead_create(request: HttpRequest) -> HttpResponse:
    if request.method == "GET":
        return render(request, "leads/form_page.html", {"form": LeadForm(initial={"page": "/zayavka/"})})

    form = LeadForm(request.POST)
    if ratelimit.is_limited(request):
        return render(request, "leads/form_page.html", {"form": form, "rate_limited": True}, status=429)
    if not form.is_valid():
        return render(request, "leads/form_page.html", {"form": form}, status=400)

    ratelimit.register_attempt(request)
    if form.is_bot:  # ловушка сработала: делаем вид, что всё хорошо, но ничего не сохраняем
        return redirect("leads:thanks")
    lead = save_lead(form.cleaned_data)
    notify_new_lead(lead.pk)
    request.session[SESSION_KEY] = lead.pk
    return redirect("leads:thanks")


def thanks(request: HttpRequest) -> HttpResponse:
    response = render(request, "leads/thanks.html", {"lead_id": request.session.get(SESSION_KEY)})
    response["X-Robots-Tag"] = "noindex"
    return response
