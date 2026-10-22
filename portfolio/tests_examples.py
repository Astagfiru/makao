import re
from datetime import date

from django.test import TestCase

from portfolio import examples, seed
from portfolio.models import DemoSite


class ExampleFeatureTests(TestCase):
    def setUp(self) -> None:
        seed.seed_portfolio()

    def free_slot(self, slug: str, service: str = "s0") -> tuple[str, str]:
        html = self.client.get(f"/primery/{slug}/?service={service}").content.decode()
        day = re.search(r'name="date" value="([0-9-]+)" checked', html).group(1)
        slot = re.search(r'name="time" value="([0-9:]+)" required>', html).group(1)
        return day, slot

    def test_old_demo_url_redirects(self) -> None:
        self.assertRedirects(self.client.get("/demo/topmen/"), "/primery/topmen/", status_code=301)

    def test_booking_payment_status_and_cabinet(self) -> None:
        day, slot = self.free_slot("topmen")
        response = self.client.post("/primery/topmen/zapis/", {"service": "s0", "date": day, "time": slot,
                                                                "name": "Тест", "consent": "on"})
        self.assertRedirects(response, "/primery/topmen/gotovo/bookings/101/")
        self.assertContains(self.client.get("/primery/topmen/gotovo/bookings/101/"), "Оплатить (тест)")
        self.client.post("/primery/topmen/oplata/bookings/101/")
        self.assertContains(self.client.get("/primery/topmen/gotovo/bookings/101/"), "Оплата прошла")
        # занятое время больше не предлагается
        html = self.client.get(f"/primery/topmen/?service=s0&date={day}").content.decode()
        self.assertIn(f'value="{slot}" required disabled', html)
        self.client.post("/primery/topmen/kabinet/", {"action": "status", "kind": "bookings", "number": "101",
                                                      "status": "Подтверждена"})
        self.assertContains(self.client.get("/primery/topmen/status/?n=101"), "№101: Подтверждена")

    def test_booking_rejected_without_consent_or_busy_slot(self) -> None:
        day, slot = self.free_slot("gradient")
        response = self.client.post("/primery/gradient/zapis/", {"service": "s0", "date": day, "time": slot})
        self.assertIn("error=1", response["Location"])
        response = self.client.post("/primery/gradient/zapis/", {"service": "s0", "date": day, "time": "03:00",
                                                                 "consent": "on"})
        self.assertIn("error=1", response["Location"])

    def test_dryclean_discount_and_order_tracking(self) -> None:
        html = self.client.get("/primery/snezhny/?q_s0=3&q_s1=2").content.decode()
        self.assertIn("Скидка 15%", html)
        self.assertNotIn("Скидка 15%", self.client.get("/primery/snezhny/?q_s0=2").content.decode())
        response = self.client.post("/primery/snezhny/zakaz/", {"q_s0": "3", "q_s1": "2", "consent": "on"})
        self.assertRedirects(response, "/primery/snezhny/gotovo/orders/101/")
        self.client.post("/primery/snezhny/kabinet/", {"action": "status", "kind": "orders", "number": "101",
                                                       "status": "Готов к выдаче"})
        self.assertContains(self.client.get("/primery/snezhny/status/?n=101"), "Готов к выдаче")
        self.assertContains(self.client.get("/primery/snezhny/status/?n=999"), "нет")

    def test_owner_edits_prices_news_and_days_off(self) -> None:
        self.client.post("/primery/topmen/kabinet/", {"action": "prices", "p_s0": "1500"})
        self.assertContains(self.client.get("/primery/topmen/"), "1 500 ₽")
        self.client.post("/primery/topmen/kabinet/", {"action": "post_add", "title": "Акция недели"})
        self.assertContains(self.client.get("/primery/topmen/"), "Акция недели")
        self.client.post("/primery/topmen/kabinet/", {"action": "post_del", "index": "0"})
        self.assertNotContains(self.client.get("/primery/topmen/"), "Акция недели")
        today = date.today().isoformat()
        self.client.post("/primery/topmen/kabinet/", {"action": "day_off", "date": today})
        self.assertContains(self.client.get("/primery/topmen/kabinet/?tab=raspisanie"), 'aria-pressed="true"')
        self.client.post("/primery/topmen/kabinet/", {"action": "reset"})
        self.assertNotContains(self.client.get("/primery/topmen/"), "1 500 ₽")

    def test_sandbox_is_private_to_visitor(self) -> None:
        self.client.post("/primery/topmen/kabinet/", {"action": "post_add", "title": "Только мне"})
        other = self.client_class()
        self.assertNotContains(other.get("/primery/topmen/"), "Только мне")

    def test_flowers_order_can_be_paid(self) -> None:
        response = self.client.post("/primery/liks-flowers/zakaz/", {"q_s0": "1", "consent": "on"})
        self.assertContains(self.client.get(response["Location"]), "Оплатить (тест)")

    def test_every_cabinet_tab_and_slots_logic(self) -> None:
        for demo in DemoSite.objects.all():
            for tab in ("zayavki", "ceny", "novosti", "raspisanie"):
                self.assertEqual(self.client.get(f"/primery/{demo.slug}/kabinet/?tab={tab}").status_code, 200)
        demo = DemoSite.objects.get(slug="snezhny")
        sunday = date(2026, 10, 25)
        self.assertEqual(examples.working_ranges(demo.blocks["hours"], sunday), [])
        self.assertEqual(len(examples.working_ranges(demo.blocks["hours"], date(2026, 10, 26))), 2)

    def test_unknown_order_is_404(self) -> None:
        self.assertEqual(self.client.get("/primery/topmen/gotovo/orders/5/").status_code, 404)
        self.assertEqual(self.client.get("/primery/topmen/gotovo/hack/5/").status_code, 404)
