from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .api import CODING_ROOT


DEFAULT_CONTRAST_GROUPS_DIR = CODING_ROOT / "data" / "contrast_groups"
DEFAULT_TASKS_DIR = CODING_ROOT / "data" / "tasks"
DEFAULT_THREATS_DIR = CODING_ROOT / "data" / "threats"
DEFAULT_SKILLS_DIR = CODING_ROOT / "data" / "skills"


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _load_ref(ref: str, directory: Path, label: str) -> dict[str, Any]:
    path = directory / f"{ref}.json"
    if not path.exists():
        raise KeyError(f"unknown {label}: {ref}")
    return read_json(path)


def iter_contrast_group_paths(contrast_groups_dir: Path = DEFAULT_CONTRAST_GROUPS_DIR) -> list[Path]:
    return sorted(contrast_groups_dir.glob("*.json"))


def load_contrast_group(path: Path) -> dict[str, Any]:
    return read_json(path)


def load_task_variant(ref: str, tasks_dir: Path = DEFAULT_TASKS_DIR) -> dict[str, Any]:
    return _load_ref(ref, tasks_dir, "task variant")


def load_threat_profile(ref: str, threats_dir: Path = DEFAULT_THREATS_DIR) -> dict[str, Any]:
    return _load_ref(ref, threats_dir, "threat profile")


def load_skill_descriptor(ref: str, skills_dir: Path = DEFAULT_SKILLS_DIR) -> dict[str, Any]:
    return _load_ref(ref, skills_dir, "skill descriptor")


def iter_case_specs(
    contrast_groups_dir: Path = DEFAULT_CONTRAST_GROUPS_DIR,
    selected: list[str] | None = None,
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    cases: list[tuple[dict[str, Any], dict[str, Any]]] = []
    selected_set = set(selected or [])
    for group_path in iter_contrast_group_paths(contrast_groups_dir):
        group = load_contrast_group(group_path)
        for variant in group.get("variants", []):
            case_id = variant.get("case_id", "")
            if selected_set and case_id not in selected_set and group.get("contrast_group_id", "") not in selected_set:
                continue
            cases.append((group, variant))
    return cases
