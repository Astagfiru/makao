import shutil
import tempfile
from pathlib import Path
from unittest import mock

from django.test import TestCase, override_settings

from portfolio import seed
from portfolio.models import Case, DemoSite
from portfolio.templatetags.demo_tags import comma, demo_photo, hours_rows, open_daily, price_groups

TMP_MEDIA = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TMP_MEDIA)
class DemoSeedTests(TestCase):
    @classmethod
    def tearDownClass(cls) -> None:
        super().tearDownClass()
        shutil.rmtree(TMP_MEDIA, ignore_errors=True)

    def test_seed_creates_six_demos_and_cases_from_research(self) -> None:
        counts = seed.seed_portfolio()
        self.assertEqual(counts, {"демо-сайты": 6, "кейсы": 6})
        self.assertEqual(seed.seed_portfolio(), {})  # повторный запуск ничего не дублирует
        demo = DemoSite.objects.get(slug="snezhny")
        self.assertEqual(len(demo.blocks["prices"]), 139)
        self.assertEqual(demo.theme, "dryclean")
        self.assertTrue(demo.sources)

    def test_refresh_overwrites_admin_edits(self) -> None:
        seed.seed_portfolio()
        DemoSite.objects.filter(slug="topmen").update(blocks={})
        Case.objects.filter(slug="topmen").update(title="Правка")
        seed.seed_portfolio(refresh=True)
        self.assertTrue(DemoSite.objects.get(slug="topmen").blocks)
        self.assertEqual(Case.objects.get(slug="topmen").title, "Барбершоп Topmen")

    def test_every_demo_page_renders_with_banner_and_noindex(self) -> None:
        seed.seed_portfolio()
        for demo in DemoSite.objects.all():
            with self.subTest(demo=demo.slug):
                response = self.client.get(demo.get_absolute_url())
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response["X-Robots-Tag"], "noindex, nofollow")
                self.assertContains(response, "Демо-концепт, не official".replace("official", "официальный"))
                self.assertContains(response, "Заказать такой сайт")
                self.assertNotContains(response, "instagram")

    def test_demo_pages_publish_no_phone_numbers(self) -> None:
        seed.seed_portfolio()
        for demo in DemoSite.objects.all():
            html = self.client.get(demo.get_absolute_url()).content.decode()
            self.assertNotRegex(html, r"\+7[\s(]*9\d\d|8[\s(-]*9\d\d[\s)-]*\d{3}", demo.slug)

    def test_photos_are_copied_and_previews_attached(self) -> None:
        seed.seed_portfolio()
        private = Path(tempfile.mkdtemp())
        try:
            (private / "topmen" / "photos").mkdir(parents=True)
            (private / "topmen" / "photos" / "door.webp").write_bytes(b"x")
            (private / "previews").mkdir()
            from PIL import Image
            Image.new("RGB", (1440, 900), "black").save(private / "previews" / "topmen.webp", "WEBP")
            with mock.patch.object(seed, "PRIVATE_DIR", private):
                copied, missing = seed.copy_demo_photos()
                attached = seed.attach_previews()
            self.assertEqual(copied, 1)
            self.assertIn("snezhny", missing)
            self.assertEqual(attached, 1)
            self.assertTrue(Case.objects.get(slug="topmen").preview.name.endswith(".webp"))
            self.assertTrue((Path(TMP_MEDIA) / "demos" / "topmen" / "door.webp").exists())
        finally:
            shutil.rmtree(private, ignore_errors=True)


class DemoFilterTests(TestCase):
    def test_hours_rows_groups_days_and_marks_day_off(self) -> None:
        week = {d: "10:00–19:00" for d in ("mon", "tue", "wed", "thu", "fri")} | {"sat": "11:00–17:00", "sun": None}
        self.assertEqual(hours_rows(week), [("Пн–Пт", "10:00–19:00"), ("Сб", "11:00–17:00"), ("Вс", "выходной")])
        self.assertEqual(hours_rows(None), [])
        self.assertFalse(open_daily(week))
        self.assertTrue(open_daily({d: "9–20" for d in ("mon", "tue", "wed", "thu", "fri", "sat", "sun")}))

    def test_price_groups_keep_order_and_fix_caps(self) -> None:
        groups = price_groups([{"category": "ШУБЫ", "name": "a"}, {"category": "прочее", "name": "b"},
                               {"category": "ШУБЫ", "name": "c"}, {"name": "d"}])
        self.assertEqual([g for g, _ in groups], ["Шубы", "Прочее", "Услуги"])
        self.assertEqual(len(groups[0][1]), 2)

    def test_comma_and_photo_filters(self) -> None:
        self.assertEqual(comma(5), "5,0")
        self.assertEqual(comma(4.9), "4,9")
        self.assertEqual(comma(None), "")
        self.assertIsNone(demo_photo(None, "x"))
