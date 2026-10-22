import shutil
import tempfile
from io import BytesIO
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from portfolio import photos
from portfolio.models import Case, DemoSite, Niche

TMP_MEDIA = tempfile.mkdtemp()


def make_case(slug: str = "dental", niche_slug: str = "stomatologiya", **extra) -> Case:
    niche, _ = Niche.objects.get_or_create(slug=niche_slug, defaults={"name": niche_slug})
    demo = DemoSite.objects.create(business_name=f"Бизнес {slug}", slug=slug, theme="dental",
                                   blocks={"name": f"Бизнес {slug}", "about": "О нас"},
                                   sources=[{"url": "https://2gis.ru/x", "what": "карточка", "checked_at": "2026-10-22"}])
    return Case.objects.create(title=f"Кейс {slug}", slug=slug, niche=niche, demo=demo, summary="Коротко",
                               task="Задача", solution="Решение", done="Дизайн\nАдаптив", **extra)


def jpeg_bytes(size=(2400, 1200)) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", size, "teal").save(buffer, "JPEG")
    return buffer.getvalue()


@override_settings(MEDIA_ROOT=TMP_MEDIA)
class PortfolioTests(TestCase):
    @classmethod
    def tearDownClass(cls) -> None:
        super().tearDownClass()
        shutil.rmtree(TMP_MEDIA, ignore_errors=True)

    def test_list_and_niche_filter_without_js(self) -> None:
        make_case("dental", "stomatologiya")
        make_case("flowers", "cvety")
        response = self.client.get(reverse("portfolio:list"))
        self.assertContains(response, "Кейс dental")
        self.assertContains(response, "Кейс flowers")
        filtered = self.client.get(reverse("portfolio:list"), {"niche": "cvety"})
        self.assertNotContains(filtered, "Кейс dental")
        self.assertContains(filtered, "Кейс flowers")
        self.assertContains(filtered, 'aria-current="true"')

    def test_unpublished_case_is_hidden(self) -> None:
        make_case("hidden", is_published=False)
        self.assertNotContains(self.client.get(reverse("portfolio:list")), "Кейс hidden")
        self.assertEqual(self.client.get(reverse("portfolio:case", args=["hidden"])).status_code, 404)

    def test_case_page_has_demo_link_badge_and_sources(self) -> None:
        case = make_case()
        response = self.client.get(case.get_absolute_url())
        self.assertContains(response, "Пример работы")
        self.assertContains(response, case.demo.get_absolute_url())
        self.assertContains(response, "https://2gis.ru/x")
        self.assertEqual(case.done_list, ["Дизайн", "Адаптив"])

    def test_demo_badge_can_be_removed(self) -> None:
        case = make_case(is_demo_project=False)
        self.assertNotContains(self.client.get(case.get_absolute_url()), "Пример работы:")

    def test_demo_page_is_noindex_with_banner(self) -> None:
        case = make_case()
        response = self.client.get(case.demo.get_absolute_url())
        self.assertEqual(response["X-Robots-Tag"], "noindex, nofollow")
        self.assertContains(response, 'content="noindex, nofollow"')
        self.assertContains(response, "Пример сайта, не официальный сайт «Бизнес dental»")
        self.assertContains(response, "Заказать такой сайт")

    def test_unpublished_demo_404(self) -> None:
        case = make_case()
        DemoSite.objects.filter(pk=case.demo.pk).update(is_published=False)
        self.assertEqual(self.client.get(case.demo.get_absolute_url()).status_code, 404)

    def test_preview_upload_is_converted_to_small_webp(self) -> None:
        case = make_case()
        case.preview = SimpleUploadedFile("shot.jpg", jpeg_bytes(), content_type="image/jpeg")
        case.save()
        self.assertTrue(case.preview.name.endswith(".webp"))
        with Image.open(case.preview.path) as image:
            self.assertEqual(image.format, "WEBP")
            self.assertLessEqual(max(image.size), 1600)

    def test_photo_resolution_prefers_private_then_stock(self) -> None:
        folder = Path(TMP_MEDIA) / "demos" / "dental"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "hero.webp").write_bytes(b"x")
        found = photos.resolve("dental", {"file": "hero.webp", "alt": "Фасад", "w": 10, "h": 5})
        self.assertEqual((found.source, found.width), ("2gis", 10))
        stock = photos.resolve("dental", {"file": "none.webp", "stock": "demos/stock/dental-diamond/cabinet.webp"})
        self.assertEqual(stock.source, "stock")
        self.assertIsNone(photos.resolve("dental", {"file": "none.webp"}))
        self.assertEqual(len(photos.resolve_many("dental", [{"file": "hero.webp"}, {"file": "no.webp"}])), 1)

    def test_admin_lists_cases(self) -> None:
        from django.contrib.auth.models import User
        make_case()
        self.client.force_login(User.objects.create_superuser("boss", "", "x-strong-123"))
        self.assertContains(self.client.get(reverse("admin:portfolio_case_changelist")), "Кейс dental")
        self.assertContains(self.client.get(reverse("admin:portfolio_demosite_changelist")), "открыть")
