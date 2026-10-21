from django.contrib import admin
from django.http import HttpRequest

from leads.models import Lead


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ("number", "created_at", "name", "phone", "short_message", "consent_mark", "status")
    list_display_links = ("number", "name")
    list_editable = ("status",)
    list_filter = ("status", "created_at")
    search_fields = ("name", "phone", "message")
    date_hierarchy = "created_at"
    readonly_fields = ("name", "phone", "message", "page", "consent", "consent_at", "policy_version",
                       "consent_version", "created_at", "updated_at")
    fieldsets = (
        ("Заявка", {"fields": ("name", "phone", "message", "page", "created_at")}),
        ("Согласие на обработку персональных данных",
         {"fields": ("consent", "consent_at", "policy_version", "consent_version")}),
        ("Работа с заявкой", {"fields": ("status", "note", "updated_at")}),
    )

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False  # заявки приходят только с сайта

    @admin.display(description="№", ordering="pk")
    def number(self, obj: Lead) -> str:
        return f"№{obj.pk}"

    @admin.display(description="Что нужно")
    def short_message(self, obj: Lead) -> str:
        return (obj.message[:60] + "…") if len(obj.message) > 60 else obj.message

    @admin.display(description="Согласие", boolean=True)
    def consent_mark(self, obj: Lead) -> bool:
        return obj.consent
