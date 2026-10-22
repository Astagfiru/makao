from django.contrib import admin
from django.utils.html import format_html

from portfolio.models import Case, DemoSite, Niche


@admin.register(Niche)
class NicheAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "order")
    list_editable = ("order",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    list_display = ("title", "niche", "preview_thumb", "is_demo_project", "is_published", "order")
    list_editable = ("is_demo_project", "is_published", "order")
    list_filter = ("niche", "is_demo_project", "is_published")
    search_fields = ("title", "summary")
    prepopulated_fields = {"slug": ("title",)}
    fieldsets = (
        (None, {"fields": ("title", "slug", "niche", "demo", "summary", "preview")}),
        ("Описание кейса", {"fields": ("task", "solution", "done")}),
        ("Показ", {"fields": ("is_demo_project", "is_published", "order")}),
    )

    @admin.display(description="Превью")
    def preview_thumb(self, obj: Case) -> str:
        if not obj.preview:
            return "—"
        return format_html('<img src="{}" alt="" style="height:40px;border-radius:4px">', obj.preview.url)


@admin.register(DemoSite)
class DemoSiteAdmin(admin.ModelAdmin):
    list_display = ("business_name", "theme", "checked_at", "is_published", "open_link")
    list_editable = ("is_published",)
    list_filter = ("theme", "is_published")
    prepopulated_fields = {"slug": ("business_name",)}
    fieldsets = (
        (None, {"fields": ("business_name", "slug", "theme", "is_published")}),
        ("Источники", {"fields": ("source_url", "checked_at", "sources")}),
        ("Содержимое (JSON)", {"fields": ("blocks",), "classes": ("collapse",)}),
    )

    @admin.display(description="Пример")
    def open_link(self, obj: DemoSite) -> str:
        return format_html('<a href="{}" target="_blank" rel="noopener">открыть ↗</a>', obj.get_absolute_url())
