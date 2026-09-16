from __future__ import annotations

import html
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class InjectionSeed:
    seed_id: str
    title: str
    delivery: str
    content: str
    category: str


_ROW = re.compile(r"^\|\s*(\d+)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*$")


def _clean(value: str) -> str:
    value = html.unescape(value).replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")
    return re.sub(r"\s+", " ", value).strip()


def load_seed_catalog(path: Path) -> list[InjectionSeed]:
    """Parse seed metadata only; source text is never interpreted or executed."""
    seeds: list[InjectionSeed] = []
    category = ""
    for raw in path.read_text(encoding="utf-8").splitlines():
        if raw.startswith("## Contextual Seeds"):
            category = "contextual"
        elif raw.startswith("## Obvious Seeds"):
            category = "obvious"
        match = _ROW.match(raw)
        if not match or not category or match.group(1) == "ID":
            continue
        seed_id, title, delivery, content = match.groups()
        seeds.append(InjectionSeed(seed_id, _clean(title), _clean(delivery), _clean(content), category))
    return seeds


def seed_by_id(path: Path, seed_id: str) -> InjectionSeed:
    requested = str(seed_id)
    category_filter = None
    if ":" in requested:
        category_filter, requested = requested.split(":", 1)
        if category_filter not in {"contextual", "obvious"}:
            raise KeyError(f"unknown seed category: {category_filter}")
    for seed in load_seed_catalog(path):
        if seed.seed_id == requested and (category_filter is None or seed.category == category_filter):
            return seed
    raise KeyError(f"unknown injection seed: {seed_id}")
