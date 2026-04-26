from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DECISIONS = {"Allow", "Deny", "Ask", "Defer", "Fallback"}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            if not isinstance(obj, dict):
                raise ValueError(f"{path}:{line_no}: expected JSON object")
            obj["_line_no"] = line_no
            rows.append(obj)
    return rows


def load_skill_set(skill_set_ref: str) -> dict[str, Any]:
    path = repo_root() / skill_set_ref
    if not path.exists():
        raise FileNotFoundError(f"skill set not found: {skill_set_ref}")
    return read_json(path)


def skill_names(skill_set: dict[str, Any]) -> set[str]:
    return {skill["name"] for skill in skill_set.get("skills", [])}


def strip_internal_fields(obj: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in obj.items() if not k.startswith("_")}

