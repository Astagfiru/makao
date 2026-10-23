"""Рабочий функционал сайтов-примеров: запись на время, оплата, корзина, статус заказа, новости, кабинет владельца.

Всё, что посетитель делает на примере, хранится только в его сессии («песочница»): видит только он,
в общую базу и настоящему бизнесу ничего не уходит, через две недели сессия истекает.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from django.http import HttpRequest
from django.utils import timezone

from portfolio.models import DemoSite

MAX_ITEMS = 30  # не даём сессии разрастаться
WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
DAY_SHORT = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]
TIME_RANGE = re.compile(r"(\d{1,2}):(\d{2})\s*[–-]\s*(\d{1,2}):(\d{2})")

# Что умеет каждый пример — по бизнес-процессу ниши.
FEATURES: dict[str, dict] = {
    # у стоматологии нет поля «что беспокоит»: это сведения о здоровье (особая категория данных)
    "dental": {"booking": {"title": "Запись на приём", "button": "Записаться", "pay": False, "step": 30},
               "posts": True},
    "dryclean": {"cart": {"title": "Рассчитать стоимость и оформить приём", "pay": False}, "tracker": True,
                 "posts": True, "branch": True},
    "barber": {"booking": {"title": "Онлайн-запись", "button": "Записаться", "pay": True, "step": 30,
                           "ask": "Пожелания мастеру (необязательно)"}, "posts": True},
    "salon": {"booking": {"title": "Онлайн-запись", "button": "Выбрать время", "pay": True, "step": 30,
                          "ask": "Длина и текущий цвет волос (необязательно)"}, "posts": True},
    "autobody": {"booking": {"title": "Запись на осмотр", "button": "Записаться на осмотр", "pay": False, "step": 60,
                             "ask": "Марка авто и что повреждено"}, "tracker": True, "posts": False},
    "flowers": {"cart": {"title": "Оформить заказ", "pay": True}, "delivery": True, "tracker": True, "posts": True},
    "cafe": {"cart": {"title": "Предзаказ навынос", "pay": True}, "pickup": True, "tracker": True, "posts": True},
    "atelier": {"booking": {"title": "Запись на мерки и примерку", "button": "Записаться", "pay": False, "step": 30,
                            "ask": "Что нужно сделать (необязательно)",
                            "intro": "Мастер снимет мерки, обсудит фасон и ткань — можно принести фото или эскиз.",
                            "places": ["В ателье — Курашова, 8, каб. 208", "Выезд мастера на дом"]},
                "tracker": True, "posts": True},
    "phonerepair": {"booking": {"title": "Сдать в ремонт", "button": "Записаться на приём", "pay": False, "step": 30,
                                "ask": "Что случилось с устройством", "devices": True,
                                "intro": "Мастер посмотрит устройство при вас; стоимость и срок назовёт после диагностики."},
                    "tracker": True, "posts": False},
}

STATUSES = {
    "booking": ["Новая", "Подтверждена", "Пришёл", "Отменена"],
    "dryclean": ["Принят", "В чистке", "Сушка и проверка", "Готов к выдаче", "Выдан"],
    "autobody": ["Записан на осмотр", "Смета согласована", "В ремонте", "Покраска и полировка", "Готов к выдаче"],
    "flowers": ["Принят", "Собираем букет", "Передан курьеру", "Доставлен"],
    "cafe": ["Принят", "Готовим", "Готов — можно забирать", "Выдан"],
    "atelier": ["Записан", "Мерки сняты", "Раскрой и пошив", "Примерка", "Готово к выдаче", "Выдано"],
    "phonerepair": ["Записан на приём", "Диагностика", "Стоимость согласована", "В ремонте", "Готов, гарантия"],
}
# У этих ниш запись — начало заказа, поэтому у записи статусы самой ниши, а не «Новая → Пришёл».
THEMED_BOOKINGS = {"autobody", "atelier", "phonerepair"}

# Кофейня: акции из карточки 2ГИС — «каждый 6-й кофе в подарок» и «15% на кофе в свою тару».
COFFEE_GROUP, STAMPS_FOR_GIFT, OWN_CUP_DISCOUNT = "Кофе", 6, 0.15
PICKUP_STEP, PICKUP_LEAD = 15, 20  # минут: шаг времени выдачи и минимум на приготовление

# Длительность услуг — настройка владельца; в источниках её нет, здесь значения для примера.
DURATIONS = {"стрижка": 60, "бород": 30, "седин": 30, "окрашив": 120, "завивк": 150, "уход": 60, "пилинг": 30,
             "реконструкц": 90, "укладк": 60, "причёск": 90, "брови": 30, "помыть": 30, "консультац": 30,
             "имплант": 60, "хирург": 60, "брекет": 60, "протез": 60, "пошив": 60, "халадаай": 60, "укорач": 30}


@dataclass
class Service:
    id: str
    name: str
    price: int | None  # минимальная цена из прайса; None — «после консультации/осмотра»
    price_text: str
    minutes: int
    group: str = ""
    winter: bool = False
    coffee: bool = False


def _price_min(text: str | None) -> int | None:
    digits = re.findall(r"\d[\d   ]*", text or "")
    return int(re.sub(r"\D", "", digits[0])) if digits else None


def _group_name(raw: str) -> str:
    """«ПУХОВИКИ (ПУХ.ПЕРО…)» -> «Пуховики (пух.перо…)»."""
    name = raw.strip()
    if name.split(" (")[0].isupper():
        name = name[:1] + name[1:].lower()
    return name[:1].upper() + name[1:]


def _minutes(name: str, default: int) -> int:
    low = name.lower()
    return next((m for key, m in DURATIONS.items() if key in low), default)


def services(demo: DemoSite) -> list[Service]:
    """Услуги для записи или позиции для корзины — из прайса 2ГИС, а где его нет — из описания услуг."""
    b = demo.blocks or {}
    step = FEATURES.get(demo.theme, {}).get("booking", {}).get("step", 60)
    items: list[Service] = []
    if demo.theme == "dental":
        items.append(Service("s0", "Бесплатная консультация", 0, "бесплатно", 30, "Первичный приём"))
        for i, s in enumerate(b.get("services_explained", []), 1):
            if s["name"] == "Снимок на месте":
                continue
            items.append(Service(f"s{i}", s["name"], None, "после консультации", _minutes(s["name"], 60), "Лечение"))
        return items
    if demo.theme == "phonerepair":
        return [Service(f"s{i}", n, None, "после диагностики", step, "Ремонт") for i, n in enumerate(b.get("repairs", []))]
    if demo.theme == "autobody":
        names = [p["name"] for p in b.get("prices", [])] + ["Ремонт вмятин без покраски (ПДР)", "Сварка"]
        return [Service(f"s{i}", f"Осмотр: {n.lower()}", None, "цена после осмотра", step, "Осмотр")
                for i, n in enumerate(names)]
    for i, p in enumerate(b.get("prices", [])):
        price = _price_min(p.get("price"))
        items.append(Service(f"s{i}", p["name"].rstrip(". "), price, p.get("price") or "по запросу",
                             _minutes(p["name"], step), _group_name(p.get("category") or "")))
    if demo.theme == "flowers":
        names = {c["name"] for c in b.get("catalog", [])}
        items = [s for s in items if s.name in names or s.group == "Вазы"]
    if demo.theme == "dryclean":
        for s in items:
            s.winter = winter_item(s)
    if demo.theme == "cafe":
        for s in items:
            s.coffee = s.group == COFFEE_GROUP
    if demo.theme == "atelier":
        for s in items:
            s.group = "Ремонт и подгонка" if s.group == "Все" else s.group
    return items


class Sandbox:
    """Данные посетителя для одного примера (живут в его сессии)."""

    def __init__(self, request: HttpRequest, demo: DemoSite) -> None:
        self.request, self.demo = request, demo
        self.key = f"example:{demo.slug}"
        self.data = request.session.get(self.key) or {"bookings": [], "orders": [], "prices": {}, "posts": [],
                                                       "days_off": [], "counter": 100}
        self.data.setdefault("stamps", 0)

    def save(self) -> None:
        for name in ("bookings", "orders", "posts"):
            self.data[name] = self.data[name][-MAX_ITEMS:]
        self.request.session[self.key] = self.data
        self.request.session.modified = True

    def next_number(self) -> int:
        self.data["counter"] += 1
        return self.data["counter"]

    # --- цены с учётом правок владельца
    def services(self) -> list[Service]:
        result = []
        for s in services(self.demo):
            override = self.data["prices"].get(s.id)
            if override is not None:
                s.price, s.price_text = override, f"{override:,} ₽".replace(",", " ")
            result.append(s)
        return result

    def service(self, sid: str) -> Service | None:
        return next((s for s in self.services() if s.id == sid), None)

    # --- записи
    def taken(self, day: date) -> set[str]:
        return {b["time"] for b in self.data["bookings"] if b["date"] == day.isoformat() and b["status"] != "Отменена"}

    def find(self, kind: str, number: int) -> dict | None:
        return next((x for x in self.data[kind] if x["number"] == number), None)


def working_ranges(hours: dict | None, day: date) -> list[tuple[time, time]]:
    text = (hours or {}).get(WEEKDAYS[day.weekday()]) or ""
    return [(time(int(a), int(b)), time(int(c), int(d))) for a, b, c, d in TIME_RANGE.findall(text)]


def booking_days(sandbox: Sandbox, count: int = 7) -> list[dict]:
    today = timezone.localdate()
    days = []
    for shift in range(count):
        day = today + timedelta(days=shift)
        off = day.isoformat() in sandbox.data["days_off"] or not working_ranges(sandbox.demo.blocks.get("hours"), day)
        days.append({"date": day, "iso": day.isoformat(), "label": f"{DAY_SHORT[day.weekday()]}, {day.day}",
                     "off": off})
    return days


def slots(sandbox: Sandbox, day: date, minutes: int) -> list[dict]:
    """Свободное время: по часам работы из 2ГИС, минус уже занятое и прошедшее."""
    if day.isoformat() in sandbox.data["days_off"]:
        return []
    step = FEATURES[sandbox.demo.theme]["booking"]["step"]
    now = timezone.localtime()
    taken = sandbox.taken(day)
    result = []
    for start, end in working_ranges(sandbox.demo.blocks.get("hours"), day):
        t = datetime.combine(day, start)
        last = datetime.combine(day, end) - timedelta(minutes=minutes)
        while t <= last:
            label = t.strftime("%H:%M")
            past = day == now.date() and t.time() <= (now + timedelta(minutes=30)).time()
            result.append({"time": label, "free": label not in taken and not past})
            t += timedelta(minutes=step)
    return result


def winter_item(service: Service) -> bool:
    """Для акции химчистки: «при сдаче от 5 зимних вещей скидка 15%»."""
    text = f"{service.group} {service.name}".lower()
    return any(w in text for w in ("пуховик", "мех", "шуб", "дублен", "утепл", "зимн", "парка"))


def coffee_discounts(sandbox: Sandbox, cups: list[int], own_cup: bool) -> tuple[list[tuple[str, int]], int]:
    """Подарочные кофе по карте гостя (каждый 6-й) и скидка за свою тару на остальные. Возвращает скидки и штампы."""
    stamps = sandbox.data["stamps"]
    gifts = (stamps + len(cups)) // STAMPS_FOR_GIFT - stamps // STAMPS_FOR_GIFT
    cups = sorted(cups)
    result = []
    if gifts:
        result.append((f"Каждый 6-й кофе в подарок: {gifts} шт.", sum(cups[:gifts])))
    if own_cup and cups[gifts:]:
        # floor(x + 0.5) — так же, как Math.round в живом расчёте на странице
        result.append(("Своя тара: −15% на кофе", math.floor(sum(cups[gifts:]) * OWN_CUP_DISCOUNT + 0.5)))
    return result, stamps + len(cups)


def cart_total(sandbox: Sandbox, quantities: dict[str, int], own_cup: bool = False) -> dict:
    lines, total, winter, unknown, cups = [], 0, 0, 0, []
    for s in sandbox.services():
        qty = quantities.get(s.id, 0)
        if qty <= 0:
            continue
        line = s.price * qty if s.price is not None else None
        lines.append({"id": s.id, "name": s.name, "qty": qty, "price_text": s.price_text, "sum": line})
        total += line or 0
        unknown += line is None
        winter += qty if winter_item(s) else 0
        cups += [s.price] * qty if s.coffee and s.price is not None else []
    discounts, stamps = [], sandbox.data["stamps"]
    if sandbox.demo.theme == "dryclean" and winter >= 5:
        discounts.append((f"Скидка 15% за {winter} зимних вещей", round(total * 0.15)))
    if sandbox.demo.theme == "cafe":
        discounts, stamps = coffee_discounts(sandbox, cups, own_cup)
    discount = sum(amount for _, amount in discounts)
    return {"lines": lines, "subtotal": total, "discounts": discounts, "discount": discount, "total": total - discount,
            "winter": winter, "unknown": unknown, "cups": len(cups), "stamps": stamps}


def pickup_slots(sandbox: Sandbox) -> list[str]:
    """Время выдачи предзаказа сегодня: не раньше чем через 20 минут и до закрытия."""
    now = timezone.localtime()
    today = now.date()
    if today.isoformat() in sandbox.data["days_off"]:
        return []
    earliest = (now + timedelta(minutes=PICKUP_LEAD)).replace(tzinfo=None)
    result = []
    for start, end in working_ranges(sandbox.demo.blocks.get("hours"), today):
        t = datetime.combine(today, start)
        while t <= datetime.combine(today, end) - timedelta(minutes=PICKUP_STEP):
            if t >= earliest:
                result.append(t.strftime("%H:%M"))
            t += timedelta(minutes=PICKUP_STEP)
    return result


def parse_quantities(data, sandbox: Sandbox) -> dict[str, int]:
    result = {}
    for s in sandbox.services():
        try:
            qty = int(data.get(f"q_{s.id}", 0) or 0)
        except (TypeError, ValueError):
            qty = 0
        if 0 < qty <= 50:
            result[s.id] = qty
    return result


def default_posts(demo: DemoSite) -> list[dict]:
    """Новости и акции, которые уже есть в открытых источниках."""
    b = demo.blocks or {}
    posts = [{"title": p["text"], "text": f"Действует: {p['valid']}." if p.get("valid") else "", "own": False}
             for p in b.get("promo", [])]
    posts += [{"title": a, "text": "", "own": False} for a in (b.get("awards") or [])[:2]]
    return posts
