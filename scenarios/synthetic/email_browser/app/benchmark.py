from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .api import EMAIL_BROWSER_ROOT


DEFAULT_CONTRAST_GROUPS_DIR = EMAIL_BROWSER_ROOT / "data" / "contrast_groups"
DEFAULT_TASKS_DIR = EMAIL_BROWSER_ROOT / "data" / "tasks"
DEFAULT_THREATS_DIR = EMAIL_BROWSER_ROOT / "data" / "threats"
DEFAULT_SKILLS_DIR = EMAIL_BROWSER_ROOT / "data" / "skills"


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def iter_contrast_group_paths(contrast_groups_dir: Path = DEFAULT_CONTRAST_GROUPS_DIR) -> list[Path]:
    return sorted(contrast_groups_dir.glob("*.json"))


def _load_ref(ref: str, directory: Path, label: str) -> dict[str, Any]:
    direct = directory / f"{ref}.json"
    if direct.exists():
        return read_json(direct)
    matches = sorted(directory.glob(f"*/{ref}.json"))
    if len(matches) == 1:
        return read_json(matches[0])
    if len(matches) > 1:
        raise KeyError(f"ambiguous {label}: {ref}")
    raise KeyError(f"unknown {label}: {ref}")


def load_task_variant(ref: str, tasks_dir: Path = DEFAULT_TASKS_DIR) -> dict[str, Any]:
    return _load_ref(ref, tasks_dir, "task variant")


def load_threat_profile(ref: str, threats_dir: Path = DEFAULT_THREATS_DIR) -> dict[str, Any]:
    return _load_ref(ref, threats_dir, "threat profile")


def load_skill_descriptor(ref: str, skills_dir: Path = DEFAULT_SKILLS_DIR) -> dict[str, Any]:
    return _load_ref(ref, skills_dir, "skill descriptor")


def compose_case_from_variant(
    group: dict[str, Any],
    variant: dict[str, Any],
    threats_dir: Path = DEFAULT_THREATS_DIR,
    tasks_dir: Path = DEFAULT_TASKS_DIR,
    skills_dir: Path = DEFAULT_SKILLS_DIR,
) -> dict[str, Any]:
    task_ref = variant["task_variant_ref"]
    threat_ref = variant["threat_profile_ref"]
    task = load_task_variant(task_ref, tasks_dir=tasks_dir)
    threat = load_threat_profile(threat_ref, threats_dir=threats_dir)
    trusted_skill = load_skill_descriptor(group["trusted_skill_ref"], skills_dir=skills_dir)
    observation_refs = []
    observation_refs.extend(threat.get("observation_refs", []))
    for overlay in (threat.get("scenario_overlays") or {}).values():
        if isinstance(overlay, dict):
            observation_refs.extend(overlay.get("observation_refs", []))

    return {
        "case_id": variant["case_id"],
        "scenario": group.get("scenario", "synthetic_email_browser"),
        "contrast_group_id": group["contrast_group_id"],
        "trusted_skill_ref": group["trusted_skill_ref"],
        "skill_under_test": group["trusted_skill_name"],
        "trusted_skill": trusted_skill,
        "task": {
            "task_type": task["task_type"],
            "task_family": task.get("task_family"),
            "operation": task.get("operation"),
            "description": task["description"],
            "authorization_boundary": task.get("authorization_boundary"),
        },
        "task_variant": task,
        "task_variant_ref": task_ref,
        "threat_profile_ref": threat_ref,
        "threat_type": threat["threat_type"],
        "threat_profile": threat,
        "observation_refs": observation_refs,
    }


def iter_case_specs(
    contrast_groups_dir: Path = DEFAULT_CONTRAST_GROUPS_DIR,
    selected: list[str] | None = None,
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    selected_set = set(selected or [])
    specs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    found: set[str] = set()
    for path in iter_contrast_group_paths(contrast_groups_dir):
        group = read_json(path)
        group_id = group["contrast_group_id"]
        for variant in group.get("variants", []):
            case_id = variant["case_id"]
            if not selected_set or case_id in selected_set or group_id in selected_set or path.stem in selected_set:
                specs.append((group, variant))
                found.update({case_id, group_id, path.stem})
    missing = selected_set - found
    if missing:
        raise ValueError(f"unknown case or contrast group(s): {', '.join(sorted(missing))}")
    return specs


def load_case(case_id_or_group: str, contrast_groups_dir: Path = DEFAULT_CONTRAST_GROUPS_DIR) -> dict[str, Any]:
    matches = iter_case_specs(contrast_groups_dir=contrast_groups_dir, selected=[case_id_or_group])
    if len(matches) == 1:
        group, variant = matches[0]
        return compose_case_from_variant(group, variant)
    if matches:
        return {
            "contrast_group_id": matches[0][0]["contrast_group_id"],
            "variants": [
                {
                    "case_id": variant["case_id"],
                    "task_variant_ref": variant.get("task_variant_ref"),
                    "threat_profile_ref": variant.get("threat_profile_ref"),
                    "trusted_skill_name": group["trusted_skill_name"],
                }
                for group, variant in matches
            ],
        }
    raise KeyError(f"unknown case: {case_id_or_group}")


def list_cases(contrast_groups_dir: Path = DEFAULT_CONTRAST_GROUPS_DIR) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for group, variant in iter_case_specs(contrast_groups_dir=contrast_groups_dir):
        cases.append(
            {
                "case_id": variant["case_id"],
                "contrast_group_id": group["contrast_group_id"],
                "trusted_skill_name": group["trusted_skill_name"],
                "task_variant_ref": variant.get("task_variant_ref"),
                "threat_profile_ref": variant.get("threat_profile_ref"),
            }
        )
    return cases


def write_jsonl(rows: list[dict[str, Any]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True) + "\n")

