from django.conf import settings
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path, re_path
from django.views.static import serve

from config.sitemaps import SITEMAPS

urlpatterns = [
    path("admin/", admin.site.urls),
    path("sitemap.xml", sitemap, {"sitemaps": SITEMAPS}, name="sitemap"),
    path("", include("core.urls")),
    path("", include("portfolio.urls")),
    path("", include("leads.urls")),
]

if settings.SERVE_MEDIA:  # на сервере /media/ отдаёт Caddy
    urlpatterns += [re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT})]

handler404 = "core.views.page_not_found"
