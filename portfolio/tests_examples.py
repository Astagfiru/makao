import re
from datetime import date, datetime, time
from unittest import mock

from django.test import TestCase
from django.utils import timezone

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


class NewNicheExampleTests(TestCase):
    """Кофейня (предзаказ навынос с акциями), ателье (мерки с выездом), ремонт телефонов (приём устройства)."""

    def setUp(self) -> None:
        seed.seed_portfolio()
        self.cafe = DemoSite.objects.get(slug="coffee-globus")
        names = {s.name: s.id for s in examples.services(self.cafe)}
        self.americano, self.syrniki = names["Американо, 300 мл"], names["Сырники"]
        morning = timezone.make_aware(datetime.combine(date(2026, 10, 22), time(10, 0)))
        patcher = mock.patch("portfolio.examples.timezone.localtime", return_value=morning)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_coffee_gifts_count_stamps_from_earlier_orders(self) -> None:
        sandbox = examples.Sandbox(mock.Mock(session={}), self.cafe)
        sandbox.data["stamps"] = 3
        discounts, stamps = examples.coffee_discounts(sandbox, [299, 209, 209], own_cup=True)
        self.assertEqual(discounts[0], ("Каждый 6-й кофе в подарок: 1 шт.", 209))
        self.assertEqual(discounts[1], ("Своя тара: −15% на кофе", 76))  # (209 + 299) × 15%
        self.assertEqual(stamps, 6)
        self.assertEqual(examples.coffee_discounts(sandbox, [209], own_cup=False), ([], 4))

    def test_cafe_preorder_with_own_cup_payment_and_status(self) -> None:
        html = self.client.get(f"/primery/coffee-globus/?q_{self.americano}=6&q_{self.syrniki}=1&own_cup=on").content.decode()
        self.assertIn("Каждый 6-й кофе в подарок: 1 шт.", html)
        self.assertIn("Своя тара", html)
        self.assertIn('<option>10:30</option>', html)
        self.assertNotIn('<option>10:15</option>', html)  # меньше 20 минут на приготовление
        response = self.client.post("/primery/coffee-globus/zakaz/", {
            f"q_{self.americano}": "6", f"q_{self.syrniki}": "1", "own_cup": "on", "slot": "10:30", "consent": "on"})
        self.assertRedirects(response, "/primery/coffee-globus/gotovo/orders/101/")
        done = self.client.get("/primery/coffee-globus/gotovo/orders/101/")
        # 6 × 209 + 419 = 1673; подарок −209; своя тара −15% от 5 × 209 = 157
        self.assertContains(done, "Итого: 1 307 ₽")
        self.assertContains(done, "−157 ₽")
        self.assertContains(done, "Оплатить (тест)")
        self.assertContains(done, "Навынос, 10:30")
        self.client.post("/primery/coffee-globus/kabinet/", {"action": "status", "kind": "orders", "number": "101",
                                                             "status": "Готов — можно забирать"})
        self.assertContains(self.client.get("/primery/coffee-globus/status/?n=101"), "Готов — можно забирать")
        # шесть штампов уже потрачены на подарок: следующий кофе — первый штамп новой карты
        html = self.client.get(f"/primery/coffee-globus/?q_{self.americano}=1").content.decode()
        self.assertNotIn("в подарок: 1 шт.", html)

    def test_cafe_preorder_needs_valid_pickup_time(self) -> None:
        response = self.client.post("/primery/coffee-globus/zakaz/", {f"q_{self.americano}": "1", "slot": "07:00",
                                                                      "consent": "on"})
        self.assertIn("error=1", response["Location"])

    def test_atelier_booking_with_home_visit_has_order_statuses(self) -> None:
        day, slot = ExampleFeatureTests.free_slot(self, "nicole")
        self.client.post("/primery/nicole/zapis/", {"service": "s0", "date": day, "time": slot, "consent": "on",
                                                    "place": "Выезд мастера на дом", "device": "Apple"})
        done = self.client.get("/primery/nicole/gotovo/bookings/101/")
        self.assertContains(done, "Выезд мастера на дом")
        self.assertNotContains(done, "Устройство")
        self.assertContains(done, "Раскрой и пошив")
        self.client.post("/primery/nicole/kabinet/", {"action": "status", "kind": "bookings", "number": "101",
                                                      "status": "Примерка"})
        self.assertContains(self.client.get("/primery/nicole/status/?n=101"), "№101: Примерка")

    def test_phone_repair_booking_keeps_device_and_repair_statuses(self) -> None:
        day, slot = ExampleFeatureTests.free_slot(self, "remont-plus")
        self.client.post("/primery/remont-plus/zapis/", {"service": "s1", "date": day, "time": slot, "consent": "on",
                                                         "device": "Xiaomi", "note": "разбит экран"})
        done = self.client.get("/primery/remont-plus/gotovo/bookings/101/")
        self.assertContains(done, "Xiaomi")
        self.assertContains(done, "Записан на приём")
        self.assertContains(done, "после диагностики")
        self.client.post("/primery/remont-plus/kabinet/", {"action": "status", "kind": "bookings", "number": "101",
                                                           "status": "Стоимость согласована"})
        self.assertContains(self.client.get("/primery/remont-plus/status/?n=101"), "Стоимость согласована")
