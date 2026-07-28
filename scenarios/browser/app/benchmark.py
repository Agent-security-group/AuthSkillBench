from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .api import BROWSER_ROOT


DEFAULT_CONTRAST_GROUPS_DIR = BROWSER_ROOT / "data" / "contrast_groups"
DEFAULT_TASKS_DIR = BROWSER_ROOT / "data" / "tasks"
DEFAULT_THREATS_DIR = BROWSER_ROOT / "data" / "threats"
DEFAULT_SKILLS_DIR = BROWSER_ROOT / "data" / "skills"
DEFAULT_OUTPUT_DIR = BROWSER_ROOT / "outputs"


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


def list_contrast_groups(contrast_groups_dir: Path = DEFAULT_CONTRAST_GROUPS_DIR) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    for path in iter_contrast_group_paths(contrast_groups_dir):
        group = read_json(path)
        groups.append(
            {
                "contrast_group_id": group["contrast_group_id"],
                "file": path.name,
                "trusted_skill_ref": group["trusted_skill_ref"],
                "trusted_skill_name": group["trusted_skill_name"],
                "variant_count": len(group.get("variants", [])),
                "case_ids": [item.get("case_id") for item in group.get("variants", [])],
            }
        )
    return groups


def load_skill_descriptor(skill_ref: str, skills_dir: Path = DEFAULT_SKILLS_DIR) -> dict[str, Any]:
    return _load_ref(skill_ref, skills_dir, "trusted skill")


def load_task_variant(task_ref: str, tasks_dir: Path = DEFAULT_TASKS_DIR) -> dict[str, Any]:
    path = tasks_dir / f"{task_ref}.json"
    if path.exists():
        return read_json(path)
    matches = sorted(tasks_dir.glob(f"*/{task_ref}.json"))
    if len(matches) == 1:
        return read_json(matches[0])
    if len(matches) > 1:
        raise KeyError(f"ambiguous task variant: {task_ref}")
    raise KeyError(f"unknown task variant: {task_ref}")


def list_task_groups(tasks_dir: Path = DEFAULT_TASKS_DIR) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    for group_dir in sorted(path for path in tasks_dir.iterdir() if path.is_dir()):
        variant_paths = sorted(group_dir.glob("*.json"))
        variants = [read_json(path) for path in variant_paths]
        groups.append(
            {
                "task_group_id": group_dir.name,
                "variant_count": len(variant_paths),
                "operations": sorted({str(variant.get("operation")) for variant in variants if variant.get("operation")}),
                "current_variant_refs": [
                    str(variant.get("task_variant_id") or path.stem)
                    for path, variant in zip(variant_paths, variants, strict=True)
                ],
                "variant_files": [str(item.relative_to(tasks_dir)) for item in variant_paths],
            }
        )
    return groups


def iter_threat_paths(threats_dir: Path = DEFAULT_THREATS_DIR) -> list[Path]:
    direct_paths = sorted(threats_dir.glob("*.json"))
    grouped_paths = sorted(threats_dir.glob("*/*.json"))
    return direct_paths + grouped_paths


def load_threat_profile(
    profile_id_or_stem: str,
    threats_dir: Path = DEFAULT_THREATS_DIR,
) -> dict[str, Any]:
    if "/" in profile_id_or_stem:
        parts = profile_id_or_stem.split("/")
        expected_stem = parts[-1]
    else:
        expected_stem = profile_id_or_stem

    for path in iter_threat_paths(threats_dir):
        profile = read_json(path)
        if (
            profile.get("threat_profile_id") == profile_id_or_stem
            or profile.get("threat_profile_id") == expected_stem
            or path.stem == profile_id_or_stem
            or path.stem == expected_stem
        ):
            return profile
    raise KeyError(f"unknown threat profile: {profile_id_or_stem}")


def list_threat_profiles(threats_dir: Path = DEFAULT_THREATS_DIR) -> list[dict[str, Any]]:
    profiles: list[dict[str, Any]] = []
    for path in iter_threat_paths(threats_dir):
        profile = read_json(path)
        profile_id = profile.get("threat_profile_id", path.stem)
        threat_type = profile.get("threat_type", profile.get("env_type", path.parent.name))
        profiles.append(
            {
                "threat_profile_id": profile_id,
                "file": str(path.relative_to(threats_dir)),
                "threat_type": threat_type,
                "threat_subtype": profile.get("threat_subtype"),
                "description": profile.get("description", profile.get("threat_description", "")),
                "state_overlay_op_count": len(profile.get("state_overlay", {}).get("ops", [])),
                "context_properties": profile.get("context_properties", {}),
            }
        )
    return profiles


def list_threat_groups(threats_dir: Path = DEFAULT_THREATS_DIR) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    for group_dir in sorted(path for path in threats_dir.iterdir() if path.is_dir()):
        profile_paths = sorted(group_dir.glob("*.json"))
        profiles = [read_json(path) for path in profile_paths]
        groups.append(
            {
                "threat_group_id": group_dir.name,
                "profile_count": len(profile_paths),
                "current_subtypes": sorted(
                    {str(profile.get("threat_subtype")) for profile in profiles if profile.get("threat_subtype")}
                ),
                "current_profile_refs": [
                    str(profile.get("threat_profile_id") or path.stem)
                    for path, profile in zip(profile_paths, profiles, strict=True)
                ],
                "profile_files": [str(item.relative_to(threats_dir)) for item in profile_paths],
            }
        )
    return groups


def compose_case_from_variant(
    group: dict[str, Any],
    variant: dict[str, Any],
    threats_dir: Path = DEFAULT_THREATS_DIR,
    tasks_dir: Path = DEFAULT_TASKS_DIR,
    skills_dir: Path = DEFAULT_SKILLS_DIR,
) -> dict[str, Any]:
    profile_ref = variant.get("threat_profile_ref")
    if not isinstance(profile_ref, str):
        raise ValueError(f"{variant.get('case_id', '<unknown>')}: threat_profile_ref is required")
    profile = load_threat_profile(profile_ref, threats_dir=threats_dir)

    task_ref = variant.get("task_variant_ref") or group.get("task_variant_ref")
    if isinstance(task_ref, str):
        task = load_task_variant(task_ref, tasks_dir=tasks_dir)
        task_summary_keys = [
            "task_type",
            "task_family",
            "operation",
            "scope",
            "authorization_surface",
            "requires_url_resolution",
            "uses_external_resource",
            "is_bulk",
            "preconditions",
            "authorization_boundary",
            "underspecifications",
            "expected_safe_behavior",
            "potential_risky_actions",
            "potential_risky_outcomes",
        ]
        task_summary = {
            "task_type": task.get("task_type", "unknown"),
            "task_family": task.get("task_family", "unknown"),
            "description": task.get("description", task.get("task_description", "")),
        }
        for key in task_summary_keys:
            if key in task:
                task_summary[key] = task[key]
    else:
        task = {}
        task_summary = {
            "task_type": group.get("task_type", "unknown"),
            "description": "",
        }

    case_id = variant["case_id"]

    trusted_skill_ref = group.get("trusted_skill_ref") or group.get("benchmark_skill_ref")
    if isinstance(trusted_skill_ref, str):
        trusted_skill = load_skill_descriptor(trusted_skill_ref, skills_dir=skills_dir)
    else:
        trusted_skill = {}

    trusted_skill_name = group.get("trusted_skill_name") or group.get("benchmark_skill_ref")

    return {
        "case_id": case_id,
        "scenario": group.get("scenario", "browser_web_search"),
        "contrast_group_id": group["contrast_group_id"],
        "trusted_skill_ref": trusted_skill_ref,
        "skill_under_test": trusted_skill_name,
        "trusted_skill": trusted_skill,
        "task": task_summary,
        "task_variant": task,
        "task_variant_ref": task_ref,
        "threat_profile_ref": profile_ref,
        "threat_type": profile.get("threat_type", "unknown"),
        "threat_profile": profile,
        "observation_refs": profile.get("observation_refs", []),
    }


def iter_case_specs(
    contrast_groups_dir: Path = DEFAULT_CONTRAST_GROUPS_DIR,
    selected: list[str] | None = None,
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    selected = selected or []
    selected_set = set(selected)
    specs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    found: set[str] = set()
    for path in iter_contrast_group_paths(contrast_groups_dir):
        group = read_json(path)
        group_id = group["contrast_group_id"]

        if "variants" in group:
            for variant in group["variants"]:
                case_id = variant["case_id"]
                if not selected_set or case_id in selected_set or group_id in selected_set or path.stem in selected_set:
                    specs.append((group, variant))
                    found.update({case_id, group_id, path.stem})

        elif "cases" in group:
            for case in group["cases"]:
                case_id = case["case_id"]
                if not selected_set or case_id in selected_set or group_id in selected_set or path.stem in selected_set:
                    specs.append((group, case))
                    found.update({case_id, group_id, path.stem})

        elif "threat_profiles" in group:
            task_variant_ref = group.get("task_variant_ref")
            env_type_from_group = group.get("env_type", "unknown")

            for tp in group["threat_profiles"]:
                if isinstance(tp, dict):
                    env_type = tp.get("env_type", env_type_from_group)
                    threat_profile_ref = tp.get("threat_profile_ref", "")
                else:
                    env_type = env_type_from_group
                    threat_profile_ref = tp

                case_id = f"{group_id}_{env_type}"
                variant = {
                    "case_id": case_id,
                    "task_variant_ref": task_variant_ref,
                    "threat_profile_ref": threat_profile_ref,
                }
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
            "trusted_skill_name": matches[0][0]["trusted_skill_name"],
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
                "trusted_skill_name": group.get("trusted_skill_name", group.get("benchmark_skill_ref", "")),
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