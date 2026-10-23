from django.contrib import admin
from django.http import HttpRequest, HttpResponseRedirect
from django.urls import reverse

from core.models import ContactChannel, FAQItem, Review, SiteSettings, Tariff

admin.site.site_header = "Кузьмин Виктор — управление сайтом"
admin.site.site_title = "Админка сайта"
admin.site.index_title = "Что будем править?"


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Оператор персональных данных (футер, политика, согласие)", {
            "fields": ("operator_name", "status", "inn", "ogrnip", "pd_email", "city", "hosting"),
        }),
        ("Версии правовых документов", {
            "fields": (("policy_version", "policy_date"), ("consent_version", "consent_date")),
            "description": "Изменили текст политики или согласия — поднимите версию и дату. "
                           "Новые заявки сохранят новую версию.",
        }),
        ("Карта на странице контактов", {"fields": ("map_embed_url",)}),
    )

    def has_add_permission(self, request: HttpRequest) -> bool:
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        return False

    def changelist_view(self, request: HttpRequest, extra_context=None):
        obj = SiteSettings.load()
        return HttpResponseRedirect(reverse("admin:core_sitesettings_change", args=[obj.pk]))


@admin.register(ContactChannel)
class ContactChannelAdmin(admin.ModelAdmin):
    list_display = ("label", "kind", "url", "show_in_header", "show_in_footer", "show_in_cta", "is_active", "order")
    list_editable = ("show_in_header", "show_in_footer", "show_in_cta", "is_active", "order")
    list_filter = ("kind", "is_active")


@admin.register(Tariff)
class TariffAdmin(admin.ModelAdmin):
    list_display = ("name", "price_from", "duration", "days_min", "days_max", "is_featured", "is_active", "order")
    list_editable = ("price_from", "duration", "days_min", "days_max", "is_featured", "is_active", "order")


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("author_name", "client_niche", "author_consent", "is_published", "order", "created_at")
    list_editable = ("author_consent", "is_published", "order")
    list_filter = ("is_published", "author_consent")
    search_fields = ("author_name", "text")
    fields = ("author_name", "client_niche", "text", "author_consent", "is_published", "order")


@admin.register(FAQItem)
class FAQItemAdmin(admin.ModelAdmin):
    list_display = ("question", "is_published", "order")
    list_editable = ("is_published", "order")
