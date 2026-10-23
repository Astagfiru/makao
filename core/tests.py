import shutil
import tempfile
from datetime import date
from io import StringIO

from django.contrib.auth.models import User
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from core.checks import admin_password_check
from core.models import ContactChannel, FAQItem, Review, SiteSettings, Tariff
from core.security import admins_with_default_password, assert_admin_password_changed
from core.templatetags.site_tags import rub

TMP_MEDIA = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TMP_MEDIA)
class PagesTests(TestCase):
    @classmethod
    def tearDownClass(cls) -> None:
        super().tearDownClass()
        shutil.rmtree(TMP_MEDIA, ignore_errors=True)

    def setUp(self) -> None:
        call_command("setup", stdout=StringIO())

    def test_main_pages_open(self) -> None:
        for name in ("core:home", "core:contacts", "core:policy", "portfolio:list",
                     "core:seo-zakazat-sajt-yakutsk", "core:seo-razrabotka-sajtov-yakutsk-cena",
                     "core:seo-sozdanie-internet-magazina-yakutsk"):
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_home_has_hero_prices_and_legal_footer(self) -> None:
        response = self.client.get(reverse("core:home"))
        self.assertContains(response, "Сайты под ключ")
        self.assertContains(response, "15 000 ₽")
        self.assertContains(response, "Информация на сайте не является публичной офертой")
        self.assertContains(response, reverse("core:policy"))
        self.assertContains(response, "WhatsApp")

    def test_unpublished_review_is_hidden(self) -> None:
        self.assertNotContains(self.client.get(reverse("core:home")), "ПРИМЕР ОТЗЫВА")

    def test_published_review_with_consent_is_shown(self) -> None:
        Review.objects.create(author_name="Ольга", text="Сайт сделали за неделю", author_consent=True,
                              is_published=True)
        self.assertContains(self.client.get(reverse("core:home")), "Сайт сделали за неделю")

    def test_security_headers(self) -> None:
        response = self.client.get(reverse("core:home"))
        self.assertIn("nonce-", response["Content-Security-Policy"])
        self.assertIn("frame-ancestors 'none'", response["Content-Security-Policy"])
        self.assertEqual(response["X-Frame-Options"], "DENY")
        self.assertIn("camera=()", response["Permissions-Policy"])

    def test_admin_has_no_site_csp(self) -> None:
        self.assertNotIn("Content-Security-Policy", self.client.get("/admin/login/"))

    def test_robots_and_sitemap(self) -> None:
        robots = self.client.get("/robots.txt").content.decode()
        self.assertIn("Disallow: /admin/", robots)
        self.assertIn("Sitemap:", robots)
        sitemap = self.client.get("/sitemap.xml").content.decode()
        self.assertIn("/zakazat-sajt-yakutsk/", sitemap)
        self.assertNotIn("/demo/", sitemap)

    def test_yandex_map_loads_only_on_click(self) -> None:
        response = self.client.get(reverse("core:contacts"))
        self.assertContains(response, "data-map-load")
        self.assertNotContains(response, "<iframe")

    def test_cookie_banner_is_hidden_until_script_decides(self) -> None:
        response = self.client.get(reverse("core:home"))
        self.assertContains(response, 'data-cookie hidden')
        self.assertContains(response, "Принять")

    def test_footer_legal_block_everywhere(self) -> None:
        site = SiteSettings.load()
        site.inn = "141234567890"
        site.save()
        for name in ("core:contacts", "portfolio:list", "core:policy"):
            response = self.client.get(reverse(name))
            self.assertContains(response, "ИНН 141234567890")
            self.assertContains(response, "не является публичной офертой")
            self.assertNotContains(response, reverse("core:consent"))

    def test_empty_requisites_are_hidden(self) -> None:
        self.assertNotContains(self.client.get(reverse("core:home")), "ИНН")

    def test_no_lead_form_by_default(self) -> None:
        ContactChannel.objects.create(kind="phone", label="+7 914 000-00-00", url="tel:+79140000000")
        for name in ("core:home", "core:contacts", "core:seo-zakazat-sajt-yakutsk"):
            response = self.client.get(reverse(name))
            self.assertNotContains(response, 'class="lead-form"')
            self.assertNotContains(response, 'name="phone"')
        self.assertContains(self.client.get(reverse("core:home")), "tel:+79140000000")
        self.assertEqual(self.client.get(reverse("core:consent")).status_code, 404)
        self.assertContains(self.client.get(reverse("core:policy")), "Сайт не собирает персональные данные")
        self.assertNotIn("/consent/", self.client.get("/sitemap.xml").content.decode())

    @override_settings(LEADS_FORM_ENABLED=True)
    def test_lead_form_can_be_switched_back_on(self) -> None:
        self.assertContains(self.client.get(reverse("core:home")), 'class="lead-form"')
        self.assertEqual(self.client.get(reverse("core:consent")).status_code, 200)
        self.assertContains(self.client.get(reverse("core:policy")), "Политика обработки персональных данных")

    def test_404_page(self) -> None:
        response = self.client.get("/net-takoy-stranicy/")
        self.assertEqual(response.status_code, 404)

    def test_policy_uses_requisites_from_admin(self) -> None:
        site = SiteSettings.load()
        site.inn, site.policy_version = "141234567890", "3.0"
        site.save()
        response = self.client.get(reverse("core:policy"))
        self.assertContains(response, "141234567890")
        self.assertContains(response, "Версия 3.0")


class ModelTests(TestCase):
    def test_site_settings_is_singleton(self) -> None:
        SiteSettings.objects.create(operator_name="A")
        SiteSettings(operator_name="B").save()
        self.assertEqual(SiteSettings.objects.count(), 1)
        self.assertEqual(SiteSettings.load().operator_name, "B")

    def test_review_name_without_surname_and_consent_rule(self) -> None:
        with self.assertRaises(ValidationError):
            Review(author_name="Ольга Петрова", text="x").full_clean()
        with self.assertRaises(ValidationError):
            Review(author_name="Ольга", text="x", is_published=True, author_consent=False).full_clean()
        Review(author_name="Ольга", text="x", is_published=True, author_consent=True).full_clean()

    def test_channel_rejects_javascript_links(self) -> None:
        with self.assertRaises(ValidationError):
            ContactChannel(kind="other", label="x", url="javascript:alert(1)").full_clean()
        ContactChannel(kind="phone", label="Позвонить", url="tel:+79140000000").full_clean()

    def test_tariff_features_and_launch_window(self) -> None:
        tariff = Tariff(name="Лендинг", price_from=15000, duration="5–7 дней", features="а\n\n б ",
                        days_min=5, days_max=7)
        self.assertEqual(tariff.feature_list, ["а", "б"])
        self.assertEqual(tariff.launch_window(date(2026, 10, 22)), (date(2026, 10, 27), date(2026, 10, 29)))
        tariff.days_max = None
        self.assertEqual(tariff.launch_window(date(2026, 10, 22))[1], None)

    def test_str(self) -> None:
        self.assertIn("15000", str(Tariff(name="Лендинг", price_from=15000)))
        self.assertEqual(str(FAQItem(question="Сколько?")), "Сколько?")
        self.assertIn("WhatsApp", str(ContactChannel(kind="whatsapp", label="Написать")))

    def test_rub_filter(self) -> None:
        self.assertEqual(rub(60000), "60 000 ₽")
        self.assertEqual(rub("oops"), "")


class AdminPasswordGuardTests(TestCase):
    def test_debug_mode_allows_default_password(self) -> None:
        User.objects.create_superuser("admin", "", "admin")
        with override_settings(DEBUG=True):
            self.assertEqual(admin_password_check(None), [])
            assert_admin_password_changed()

    def test_production_refuses_default_password(self) -> None:
        User.objects.create_superuser("admin", "", "admin")
        with override_settings(DEBUG=False):
            self.assertEqual(admins_with_default_password(), ["admin"])
            self.assertEqual(admin_password_check(None)[0].id, "core.E001")
            with self.assertRaises(ImproperlyConfigured):
                assert_admin_password_changed()

    def test_production_allows_strong_password(self) -> None:
        User.objects.create_superuser("admin", "", "Strong-Pass-2026")
        with override_settings(DEBUG=False):
            self.assertEqual(admin_password_check(None), [])
            assert_admin_password_changed()


@override_settings(MEDIA_ROOT=TMP_MEDIA)
class SetupCommandTests(TestCase):
    def test_setup_creates_admin_and_content_and_is_idempotent(self) -> None:
        out = StringIO()
        call_command("setup", stdout=out)
        call_command("setup", stdout=out)
        self.assertEqual(Tariff.objects.count(), 3)
        self.assertEqual(User.objects.filter(is_superuser=True).count(), 1)
        self.assertIn("уже есть", out.getvalue())

    @override_settings(ADMIN_PASSWORD="New-Pass-2026")
    def test_reset_admin_password(self) -> None:
        User.objects.create_superuser("admin", "", "old")
        call_command("setup", "--reset-admin-password", stdout=StringIO())
        self.assertTrue(User.objects.get(username="admin").check_password("New-Pass-2026"))

    def test_site_settings_admin_redirects_to_single_record(self) -> None:
        admin = User.objects.create_superuser("boss", "", "x-strong-123")
        self.client.force_login(admin)
        response = self.client.get(reverse("admin:core_sitesettings_changelist"))
        self.assertRedirects(response, reverse("admin:core_sitesettings_change", args=[1]))
