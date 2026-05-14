from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .api import DEFAULT_STATE_PATH, EMAIL_ROOT
from .oracle import build_sample
from .runtime import EmailSandbox


DEFAULT_CONTRAST_GROUPS_DIR = EMAIL_ROOT / "data" / "contrast_groups"
DEFAULT_TASK_VARIANTS_DIR = EMAIL_ROOT / "data" / "task_variants"
DEFAULT_CANDIDATE_FIXTURES_DIR = EMAIL_ROOT / "data" / "candidate_fixtures"
DEFAULT_ENVIRONMENTS_DIR = EMAIL_ROOT / "data" / "environments"
DEFAULT_SKILLS_DIR = EMAIL_ROOT / "data" / "skills"


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
                "decision_hints": [item.get("expected_decision_hint") for item in group.get("variants", [])],
            }
        )
    return groups


def load_skill_descriptor(skill_ref: str, skills_dir: Path = DEFAULT_SKILLS_DIR) -> dict[str, Any]:
    return _load_ref(skill_ref, skills_dir, "trusted skill")


def load_task_variant(task_ref: str, task_variants_dir: Path = DEFAULT_TASK_VARIANTS_DIR) -> dict[str, Any]:
    return _load_ref(task_ref, task_variants_dir, "task variant")


def load_candidate_fixture(
    candidate_ref: str,
    candidate_fixtures_dir: Path = DEFAULT_CANDIDATE_FIXTURES_DIR,
) -> dict[str, Any]:
    return _load_ref(candidate_ref, candidate_fixtures_dir, "candidate fixture")


def iter_environment_paths(environments_dir: Path = DEFAULT_ENVIRONMENTS_DIR) -> list[Path]:
    return sorted(environments_dir.glob("*.json"))


def load_environment_profile(
    profile_id_or_stem: str,
    environments_dir: Path = DEFAULT_ENVIRONMENTS_DIR,
) -> dict[str, Any]:
    for path in iter_environment_paths(environments_dir):
        profile = read_json(path)
        if profile.get("environment_profile_id") == profile_id_or_stem or path.stem == profile_id_or_stem:
            return profile
    raise KeyError(f"unknown environment profile: {profile_id_or_stem}")


def list_environment_profiles(environments_dir: Path = DEFAULT_ENVIRONMENTS_DIR) -> list[dict[str, Any]]:
    profiles: list[dict[str, Any]] = []
    for path in iter_environment_paths(environments_dir):
        profile = read_json(path)
        profiles.append(
            {
                "environment_profile_id": profile["environment_profile_id"],
                "file": path.name,
                "environment_type": profile["environment_type"],
                "description": profile.get("description", ""),
                "context_properties": profile.get("context_properties", {}),
            }
        )
    return profiles


def compose_case_from_variant(
    group: dict[str, Any],
    variant: dict[str, Any],
    environments_dir: Path = DEFAULT_ENVIRONMENTS_DIR,
    task_variants_dir: Path = DEFAULT_TASK_VARIANTS_DIR,
    candidate_fixtures_dir: Path = DEFAULT_CANDIDATE_FIXTURES_DIR,
    skills_dir: Path = DEFAULT_SKILLS_DIR,
) -> dict[str, Any]:
    """Combine contrast-group refs into the oracle-facing sample shape.

    The task and environment profile define the initial context. The candidate
    fixture represents the call captured after an agent has run in that context.
    """

    profile_ref = variant.get("environment_profile_ref")
    if not isinstance(profile_ref, str):
        raise ValueError(f"{variant.get('case_id', '<unknown>')}: environment_profile_ref is required")
    profile = load_environment_profile(profile_ref, environments_dir=environments_dir)
    task_ref = variant.get("task_variant_ref")
    if not isinstance(task_ref, str):
        raise ValueError(f"{variant.get('case_id', '<unknown>')}: task_variant_ref is required")
    task = load_task_variant(task_ref, task_variants_dir=task_variants_dir)
    candidate_ref = variant.get("candidate_fixture_ref")
    if not isinstance(candidate_ref, str):
        raise ValueError(f"{variant.get('case_id', '<unknown>')}: candidate_fixture_ref is required")
    candidate_fixture = load_candidate_fixture(candidate_ref, candidate_fixtures_dir=candidate_fixtures_dir)
    candidate = candidate_fixture.get("candidate_invocation")
    if not isinstance(candidate, dict):
        raise ValueError(f"{candidate_ref}: candidate_invocation is required")
    trusted_skill = load_skill_descriptor(group["trusted_skill_ref"], skills_dir=skills_dir)
    return {
        "case_id": variant["case_id"],
        "scenario": group.get("scenario", "email_communication_agent"),
        "contrast_group_id": group["contrast_group_id"],
        "trusted_skill_ref": group["trusted_skill_ref"],
        "skill_under_test": group["trusted_skill_name"],
        "trusted_skill": trusted_skill,
        "task": {
            "task_type": task["task_type"],
            "description": task["description"],
        },
        "task_variant": task,
        "task_variant_ref": task_ref,
        "environment_profile_ref": profile_ref,
        "environment_type": profile["environment_type"],
        "environment_profile": profile,
        "observation_refs": profile.get("observation_refs", []),
        "captured_candidate_ref": candidate_ref,
        "candidate_invocation": candidate,
        "expected_decision_hint": variant.get("expected_decision_hint"),
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
            "trusted_skill_name": matches[0][0]["trusted_skill_name"],
            "variants": [
                {
                    "case_id": variant["case_id"],
                    "task_variant_ref": variant.get("task_variant_ref"),
                    "environment_profile_ref": variant.get("environment_profile_ref"),
                    "candidate_fixture_ref": variant.get("candidate_fixture_ref"),
                    "expected_decision_hint": variant.get("expected_decision_hint"),
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
                "expected_decision_hint": variant.get("expected_decision_hint"),
                "task_variant_ref": variant.get("task_variant_ref"),
                "environment_profile_ref": variant.get("environment_profile_ref"),
                "candidate_fixture_ref": variant.get("candidate_fixture_ref"),
            }
        )
    return cases


def generate_sample_from_spec(
    group: dict[str, Any],
    variant: dict[str, Any],
    state_path: Path = DEFAULT_STATE_PATH,
    environments_dir: Path = DEFAULT_ENVIRONMENTS_DIR,
    task_variants_dir: Path = DEFAULT_TASK_VARIANTS_DIR,
    candidate_fixtures_dir: Path = DEFAULT_CANDIDATE_FIXTURES_DIR,
    skills_dir: Path = DEFAULT_SKILLS_DIR,
) -> dict[str, Any]:
    sandbox = EmailSandbox.load(state_path)
    return build_sample(
        sandbox,
        compose_case_from_variant(
            group,
            variant,
            environments_dir=environments_dir,
            task_variants_dir=task_variants_dir,
            candidate_fixtures_dir=candidate_fixtures_dir,
            skills_dir=skills_dir,
        ),
    )


def generate_sample(
    case_or_variant: dict[str, Any],
    state_path: Path = DEFAULT_STATE_PATH,
    environments_dir: Path = DEFAULT_ENVIRONMENTS_DIR,
) -> dict[str, Any]:
    """Generate one sample from an already composed oracle case."""

    sandbox = EmailSandbox.load(state_path)
    if "candidate_invocation" in case_or_variant and "environment_type" in case_or_variant:
        return build_sample(sandbox, case_or_variant)
    raise ValueError("generate_sample expects a composed oracle case from load_case or compose_case_from_variant")


def generate_samples(
    selected: list[str] | None = None,
    state_path: Path = DEFAULT_STATE_PATH,
    contrast_groups_dir: Path = DEFAULT_CONTRAST_GROUPS_DIR,
    environments_dir: Path = DEFAULT_ENVIRONMENTS_DIR,
    task_variants_dir: Path = DEFAULT_TASK_VARIANTS_DIR,
    candidate_fixtures_dir: Path = DEFAULT_CANDIDATE_FIXTURES_DIR,
    skills_dir: Path = DEFAULT_SKILLS_DIR,
) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    for group, variant in iter_case_specs(contrast_groups_dir=contrast_groups_dir, selected=selected):
        samples.append(
            generate_sample_from_spec(
                group,
                variant,
                state_path=state_path,
                environments_dir=environments_dir,
                task_variants_dir=task_variants_dir,
                candidate_fixtures_dir=candidate_fixtures_dir,
                skills_dir=skills_dir,
            )
        )
    return samples


def write_jsonl(rows: list[dict[str, Any]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True) + "\n")
