from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .api import DEFAULT_STATE_PATH, EMAIL_ROOT
from .runtime import EmailSandbox


DEFAULT_CONTRAST_GROUPS_DIR = EMAIL_ROOT / "data" / "contrast_groups"
DEFAULT_TASK_VARIANTS_DIR = EMAIL_ROOT / "data" / "task_variants"
DEFAULT_TASK_GROUPS_DIR = EMAIL_ROOT / "data" / "task_groups"
DEFAULT_CANDIDATE_FIXTURES_DIR = EMAIL_ROOT / "data" / "candidate_fixtures"
DEFAULT_ENVIRONMENTS_DIR = EMAIL_ROOT / "data" / "environments"
DEFAULT_ENVIRONMENT_GROUPS_DIR = EMAIL_ROOT / "data" / "environment_groups"
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
                "case_ids": [item.get("case_id") for item in group.get("variants", [])],
            }
        )
    return groups


def load_skill_descriptor(skill_ref: str, skills_dir: Path = DEFAULT_SKILLS_DIR) -> dict[str, Any]:
    return _load_ref(skill_ref, skills_dir, "trusted skill")


def load_task_variant(task_ref: str, task_variants_dir: Path = DEFAULT_TASK_VARIANTS_DIR) -> dict[str, Any]:
    return _load_ref(task_ref, task_variants_dir, "task variant")


def list_task_groups(task_groups_dir: Path = DEFAULT_TASK_GROUPS_DIR) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    for path in sorted(task_groups_dir.glob("*.json")):
        group = read_json(path)
        groups.append(
            {
                "task_group_id": group["task_group_id"],
                "file": path.name,
                "description": group.get("description", ""),
                "operations": group.get("operations", []),
                "current_variant_refs": group.get("current_variant_refs", []),
                "coverage_axes": group.get("coverage_axes", []),
                "planned_variant_types": group.get("planned_variant_types", []),
            }
        )
    return groups


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
                "environment_subtype": profile.get("environment_subtype"),
                "description": profile.get("description", ""),
                "state_overlay_op_count": len(profile.get("state_overlay", {}).get("ops", [])),
                "context_properties": profile.get("context_properties", {}),
            }
        )
    return profiles


def list_environment_groups(environment_groups_dir: Path = DEFAULT_ENVIRONMENT_GROUPS_DIR) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    for path in sorted(environment_groups_dir.glob("*.json")):
        group = read_json(path)
        groups.append(
            {
                "environment_group_id": group["environment_group_id"],
                "file": path.name,
                "description": group.get("description", ""),
                "current_subtypes": group.get("current_subtypes", []),
                "current_profile_refs": group.get("current_profile_refs", []),
                "planned_subtypes": group.get("planned_subtypes", []),
            }
        )
    return groups


def compose_case_from_variant(
    group: dict[str, Any],
    variant: dict[str, Any],
    environments_dir: Path = DEFAULT_ENVIRONMENTS_DIR,
    task_variants_dir: Path = DEFAULT_TASK_VARIANTS_DIR,
    candidate_fixtures_dir: Path = DEFAULT_CANDIDATE_FIXTURES_DIR,
    skills_dir: Path = DEFAULT_SKILLS_DIR,
) -> dict[str, Any]:
    """Combine contrast-group refs into the runtime case shape.

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
    task_summary_keys = [
        "task_type",
        "task_family",
        "operation",
        "scope",
        "message_features",
        "authorization_surface",
        "requires_recipient_resolution",
        "uses_attachment",
        "is_bulk",
        "preconditions",
    ]
    task_summary = {
        "task_type": task["task_type"],
        "description": task["description"],
    }
    for key in task_summary_keys:
        if key in task:
            task_summary[key] = task[key]

    return {
        "case_id": variant["case_id"],
        "scenario": group.get("scenario", "email_communication_agent"),
        "contrast_group_id": group["contrast_group_id"],
        "trusted_skill_ref": group["trusted_skill_ref"],
        "skill_under_test": group["trusted_skill_name"],
        "trusted_skill": trusted_skill,
        "task": task_summary,
        "task_variant": task,
        "task_variant_ref": task_ref,
        "environment_profile_ref": profile_ref,
        "environment_type": profile["environment_type"],
        "environment_profile": profile,
        "observation_refs": profile.get("observation_refs", []),
        "captured_candidate_ref": candidate_ref,
        "candidate_invocation": candidate,
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
                "environment_profile_ref": variant.get("environment_profile_ref"),
                "candidate_fixture_ref": variant.get("candidate_fixture_ref"),
            }
        )
    return cases


def build_case_record(
    sandbox: EmailSandbox,
    case: dict[str, Any],
    apply_candidate: bool = False,
) -> dict[str, Any]:
    sandbox.apply_environment_profile(case.get("environment_profile"))
    sandbox.reset_trace()
    environment, observations = sandbox.build_environment(case.get("observation_refs", []))
    observation_trace = sandbox.public_trace()
    candidate_result = sandbox.run_invocation(case["candidate_invocation"], apply=apply_candidate)
    return {
        "case_id": case["case_id"],
        "scenario": case.get("scenario", "email_communication_agent"),
        "contrast_group_id": case["contrast_group_id"],
        "trusted_skill_ref": case["trusted_skill_ref"],
        "skill_under_test": case["skill_under_test"],
        "trusted_skill": case["trusted_skill"],
        "task": case["task"],
        "task_variant": case["task_variant"],
        "task_variant_ref": case["task_variant_ref"],
        "environment_profile_ref": case["environment_profile_ref"],
        "environment": {
            "environment_type": case["environment_type"],
            "environment_subtype": case.get("environment_profile", {}).get("environment_subtype"),
            "source": environment["source"],
            "content": environment["content"],
        },
        "environment_profile": case["environment_profile"],
        "agent_observations": [{"ref": item["ref"], "visible": item["visible"]} for item in observations],
        "candidate_fixture_ref": case.get("captured_candidate_ref"),
        "candidate_invocation": case["candidate_invocation"],
        "candidate_result": candidate_result,
        "runtime_metadata": {
            "environment_snapshot_id": sandbox.state.get("snapshot_id"),
            "applied_environment_overlays": sandbox.state.get("applied_environment_overlays", []),
            "observation_trace": observation_trace,
            "tool_trace": sandbox.public_trace(),
            "candidate_apply_side_effects": apply_candidate,
        },
    }


def generate_case_from_spec(
    group: dict[str, Any],
    variant: dict[str, Any],
    state_path: Path = DEFAULT_STATE_PATH,
    environments_dir: Path = DEFAULT_ENVIRONMENTS_DIR,
    task_variants_dir: Path = DEFAULT_TASK_VARIANTS_DIR,
    candidate_fixtures_dir: Path = DEFAULT_CANDIDATE_FIXTURES_DIR,
    skills_dir: Path = DEFAULT_SKILLS_DIR,
) -> dict[str, Any]:
    sandbox = EmailSandbox.load(state_path)
    return build_case_record(
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


def generate_case(
    case_or_variant: dict[str, Any],
    state_path: Path = DEFAULT_STATE_PATH,
    environments_dir: Path = DEFAULT_ENVIRONMENTS_DIR,
) -> dict[str, Any]:
    """Generate one runnable case record from an already composed case."""

    sandbox = EmailSandbox.load(state_path)
    if "candidate_invocation" in case_or_variant and "environment_type" in case_or_variant:
        return build_case_record(sandbox, case_or_variant)
    raise ValueError("generate_case expects a composed case from load_case or compose_case_from_variant")


def generate_cases(
    selected: list[str] | None = None,
    state_path: Path = DEFAULT_STATE_PATH,
    contrast_groups_dir: Path = DEFAULT_CONTRAST_GROUPS_DIR,
    environments_dir: Path = DEFAULT_ENVIRONMENTS_DIR,
    task_variants_dir: Path = DEFAULT_TASK_VARIANTS_DIR,
    candidate_fixtures_dir: Path = DEFAULT_CANDIDATE_FIXTURES_DIR,
    skills_dir: Path = DEFAULT_SKILLS_DIR,
) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for group, variant in iter_case_specs(contrast_groups_dir=contrast_groups_dir, selected=selected):
        cases.append(
            generate_case_from_spec(
                group,
                variant,
                state_path=state_path,
                environments_dir=environments_dir,
                task_variants_dir=task_variants_dir,
                candidate_fixtures_dir=candidate_fixtures_dir,
                skills_dir=skills_dir,
            )
        )
    return cases


def write_jsonl(rows: list[dict[str, Any]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True) + "\n")
