from django.urls import path

from core import views
from core.content import SEO_PAGES

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("contacts/", views.contacts, name="contacts"),
    path("policy/", views.policy, name="policy"),
    path("consent/", views.consent, name="consent"),
    path("robots.txt", views.robots_txt, name="robots"),
] + [path(f"{slug}/", views.seo_page, {"slug": slug}, name=f"seo-{slug}") for slug in SEO_PAGES]
