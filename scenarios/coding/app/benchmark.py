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


def compose_case_from_variant(
    group: dict,
    variant: dict,
    threats_dir: Path = DEFAULT_THREATS_DIR,
    tasks_dir: Path = DEFAULT_TASKS_DIR,
    skills_dir: Path = DEFAULT_SKILLS_DIR,
) -> dict:
    profile_ref = variant["threat_profile_ref"]
    profile = load_threat_profile(profile_ref, threats_dir=threats_dir)
    task_ref = variant["task_variant_ref"]
    task = load_task_variant(task_ref, tasks_dir=tasks_dir)
    skill = load_skill_descriptor(group["trusted_skill_ref"], skills_dir=skills_dir)
    return {
        "case_id": variant["case_id"],
        "contrast_group_id": group["contrast_group_id"],
        "trusted_skill_ref": group["trusted_skill_ref"],
        "skill_under_test": group["trusted_skill_name"],
        "trusted_skill": skill,
        "task": {"task_type": task["task_type"], "description": task["description"]},
        "task_variant": task,
        "task_variant_ref": task_ref,
        "threat_profile_ref": profile_ref,
        "threat_type": profile["threat_type"],
        "threat_profile": profile,
    }


def list_threat_groups(threats_dir: Path = DEFAULT_THREATS_DIR) -> list[dict]:
    groups: list[dict] = []
    for group_dir in sorted(p for p in threats_dir.iterdir() if p.is_dir()):
        profiles = [json.load(open(f, encoding="utf-8")) for f in sorted(group_dir.glob("*.json"))]
        groups.append({"threat_group_id": group_dir.name, "profile_count": len(profiles), "threat_types": sorted({p.get("threat_type","") for p in profiles})})
    return groups


def list_task_groups(tasks_dir: Path = DEFAULT_TASKS_DIR) -> list[dict]:
    groups: list[dict] = []
    for group_dir in sorted(p for p in tasks_dir.iterdir() if p.is_dir()):
        variants = [json.load(open(f, encoding="utf-8")) for f in sorted(group_dir.glob("*.json"))]
        groups.append({"task_group_id": group_dir.name, "variant_count": len(variants), "operations": sorted({v.get("operation","") for v in variants})})
    return groups


def load_case(case_id_or_group: str, contrast_groups_dir: Path = DEFAULT_CONTRAST_GROUPS_DIR) -> dict:
    matches = iter_case_specs(contrast_groups_dir=contrast_groups_dir, selected=[case_id_or_group])
    if len(matches) == 1:
        group, variant = matches[0]
        return compose_case_from_variant(group, variant)
    if matches:
        return {"contrast_group_id": matches[0][0]["contrast_group_id"], "variants": [{"case_id": v["case_id"], "task_variant_ref": v.get("task_variant_ref"), "threat_profile_ref": v.get("threat_profile_ref")} for _, v in matches]}
    raise KeyError(f"unknown case: {case_id_or_group}")


def list_cases(contrast_groups_dir: Path = DEFAULT_CONTRAST_GROUPS_DIR) -> list[dict]:
    cases: list[dict] = []
    for group, variant in iter_case_specs(contrast_groups_dir=contrast_groups_dir):
        cases.append({"case_id": variant["case_id"], "contrast_group_id": group["contrast_group_id"], "task_variant_ref": variant.get("task_variant_ref"), "threat_profile_ref": variant.get("threat_profile_ref")})
    return cases


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
