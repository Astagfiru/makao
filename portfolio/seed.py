"""Демо-сайты и кейсы: факты из docs/research/<slug>.json + тексты демо из portfolio/demos/<slug>.json."""
import json
import shutil
from datetime import date
from pathlib import Path

from django.conf import settings

from portfolio.models import Case, DemoSite, Niche

RESEARCH_DIR = settings.BASE_DIR / "docs" / "research"
DEMOS_DIR = Path(__file__).resolve().parent / "demos"
PRIVATE_DIR = settings.BASE_DIR / "research-private"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def demo_specs() -> list[dict]:
    """Тексты демо + факты исследования. Демо без файла исследования пропускается."""
    specs = []
    for path in sorted(DEMOS_DIR.glob("*.json")):
        spec = load_json(path)
        research_file = RESEARCH_DIR / f"{spec['slug']}.json"
        if research_file.exists():
            specs.append({**spec, "research": load_json(research_file)})
    return specs


def blocks_for(spec: dict) -> dict:
    """Блоки страницы: факты исследования (часы, цены, адрес…) + тексты демо. Тексты демо важнее."""
    r = spec["research"]
    facts = {key: r.get(key) for key in (
        "name", "niche", "address", "branches", "hours", "features", "about", "slogan", "since", "services",
        "promo", "awards", "priority", "prices", "prices_updated", "prices_note", "rating", "review_themes",
        "process", "photos", "card_url", "checked_at")}
    return {**facts, **spec.get("blocks", {})}


def seed_portfolio(refresh: bool = False) -> dict[str, int]:
    counts = {"демо-сайты": 0, "кейсы": 0}
    for order, spec in enumerate(demo_specs(), 1):
        r = spec["research"]
        niche, _ = Niche.objects.get_or_create(slug=spec["niche"]["slug"],
                                               defaults={"name": spec["niche"]["name"], "order": order})
        demo_values = {
            "business_name": r["name"], "theme": spec["theme"], "blocks": blocks_for(spec),
            "sources": r.get("sources", []), "source_url": r.get("card_url", ""),
            "checked_at": date.fromisoformat(r["checked_at"]),
        }
        demo = DemoSite.objects.filter(slug=spec["slug"]).first()
        if demo is None:
            demo = DemoSite.objects.create(slug=spec["slug"], **demo_values)
            counts["демо-сайты"] += 1
        elif refresh:
            DemoSite.objects.filter(pk=demo.pk).update(**demo_values)
            counts["демо-сайты"] += 1
        case = spec["case"]
        case_values = {"title": case["title"], "niche": niche, "demo": demo, "summary": case["summary"],
                       "task": case["task"], "solution": case["solution"], "done": "\n".join(case["done"]),
                       "order": order}
        exists = Case.objects.filter(slug=spec["slug"]).exists()
        if not exists:
            Case.objects.create(slug=spec["slug"], **case_values)
            counts["кейсы"] += 1
        elif refresh:
            Case.objects.filter(slug=spec["slug"]).update(**case_values)
            counts["кейсы"] += 1
    return {name: n for name, n in counts.items() if n}


def copy_demo_photos() -> tuple[int, list[str]]:
    """research-private/<slug>/photos/*.webp -> media/demos/<slug>/ (в публичном репозитории этих фото нет)."""
    copied, missing = 0, []
    for spec in demo_specs():
        src = PRIVATE_DIR / spec["slug"] / "photos"
        files = sorted(src.glob("*.webp")) if src.is_dir() else []
        if not files:
            missing.append(spec["slug"])
            continue
        dst = Path(settings.MEDIA_ROOT) / "demos" / spec["slug"]
        dst.mkdir(parents=True, exist_ok=True)
        for f in files:
            target = dst / f.name
            if not target.exists() or target.stat().st_mtime < f.stat().st_mtime:
                shutil.copy2(f, target)
                copied += 1
    return copied, missing
