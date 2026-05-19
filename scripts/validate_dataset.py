#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
from typing import Any

from common import DECISIONS, load_skill_set, read_jsonl, skill_names


SCENARIOS = {
    "repository_coding_agent",
    "email_communication_agent",
    "cloud_devops_workflow",
    "data_analysis_report_agent",
}

TASK_TYPES = {
    "send_single_message",
    "summarize_external_content",
    "send_meeting_agenda",
    "send_vendor_status_update",
    "create_reply_draft",
    "send_with_attachment",
    "forward_message_thread",
    "delete_messages_by_date",
    "batch_archive_by_label",
    "export_messages",
}

ENV_TYPES = {"benign", "adversarial_untrusted", "ambiguous"}

ENV_SUBTYPES = {
    "approved_copy_available",
    "trusted_thread_supports_task",
    "data_exfiltration_prompt_injection",
    "recipient_substitution",
    "authority_spoofing",
    "goal_hijack",
    "recipient_identity_ambiguous",
    "stale_state",
    "bulk_scope_ambiguous",
    "attachment_sensitivity_unclear",
}

REQUIRED_TOP_LEVEL = {
    "sample_id",
    "scenario",
    "contrast_group_id",
    "task",
    "environment",
    "skill_set_ref",
    "candidate_invocation",
    "expected_decision",
    "gold_rationale",
    "hidden_metadata",
}

REQUIRED_METADATA = {
    "risk_type",
    "sensitive_data_involved",
    "has_low_privilege_alternative",
    "claimed_reason_source",
}


def require(condition: bool, errors: list[str], sample_id: str, message: str) -> None:
    if not condition:
        errors.append(f"{sample_id}: {message}")


def validate_invocation(
    invocation: Any,
    errors: list[str],
    sample_id: str,
    field_name: str,
    available_skills: set[str],
) -> None:
    require(isinstance(invocation, dict), errors, sample_id, f"{field_name} must be an object")
    if not isinstance(invocation, dict):
        return
    require("skill" in invocation, errors, sample_id, f"{field_name}.skill is required")
    require("arguments" in invocation, errors, sample_id, f"{field_name}.arguments is required")
    if "skill" in invocation:
        require(
            invocation["skill"] in available_skills,
            errors,
            sample_id,
            f"{field_name}.skill {invocation['skill']!r} is not in skill set",
        )
    if "arguments" in invocation:
        require(isinstance(invocation["arguments"], dict), errors, sample_id, f"{field_name}.arguments must be an object")


def validate_dataset(path: Path) -> list[str]:
    rows = read_jsonl(path)
    errors: list[str] = []
    sample_ids: set[str] = set()
    groups: dict[str, list[str]] = defaultdict(list)
    skill_cache: dict[str, tuple[dict[str, Any], set[str]]] = {}

    for row in rows:
        sample_id = row.get("sample_id", f"line_{row.get('_line_no', '?')}")

        missing = REQUIRED_TOP_LEVEL - set(row)
        require(not missing, errors, sample_id, f"missing required fields: {sorted(missing)}")

        require(sample_id not in sample_ids, errors, sample_id, "duplicate sample_id")
        sample_ids.add(sample_id)

        scenario = row.get("scenario")
        require(scenario in SCENARIOS, errors, sample_id, f"unknown scenario {scenario!r}")

        task = row.get("task")
        require(isinstance(task, dict), errors, sample_id, "task must be an object")
        if isinstance(task, dict):
            require(task.get("task_type") in TASK_TYPES, errors, sample_id, f"unknown task_type {task.get('task_type')!r}")
            require(isinstance(task.get("description"), str) and bool(task.get("description")), errors, sample_id, "task.description must be non-empty")

        environment = row.get("environment")
        require(isinstance(environment, dict), errors, sample_id, "environment must be an object")
        if isinstance(environment, dict):
            require(environment.get("environment_type") in ENV_TYPES, errors, sample_id, f"unknown environment_type {environment.get('environment_type')!r}")
            if "environment_subtype" in environment:
                require(
                    environment.get("environment_subtype") in ENV_SUBTYPES,
                    errors,
                    sample_id,
                    f"unknown environment_subtype {environment.get('environment_subtype')!r}",
                )
            require(isinstance(environment.get("source"), str) and bool(environment.get("source")), errors, sample_id, "environment.source must be non-empty")
            require(isinstance(environment.get("content"), str) and bool(environment.get("content")), errors, sample_id, "environment.content must be non-empty")

        decision = row.get("expected_decision")
        require(decision in DECISIONS, errors, sample_id, f"unknown decision {decision!r}")
        groups[row.get("contrast_group_id", "")].append(decision)

        metadata = row.get("hidden_metadata")
        require(isinstance(metadata, dict), errors, sample_id, "hidden_metadata must be an object")
        if isinstance(metadata, dict):
            missing_meta = REQUIRED_METADATA - set(metadata)
            require(not missing_meta, errors, sample_id, f"missing metadata fields: {sorted(missing_meta)}")
            if decision == "Fallback":
                require(metadata.get("has_low_privilege_alternative") is True, errors, sample_id, "Fallback samples must set has_low_privilege_alternative=true")

        skill_set_ref = row.get("skill_set_ref")
        if isinstance(skill_set_ref, str):
            if skill_set_ref not in skill_cache:
                try:
                    skill_set = load_skill_set(skill_set_ref)
                except FileNotFoundError as exc:
                    errors.append(f"{sample_id}: {exc}")
                    continue
                skill_cache[skill_set_ref] = (skill_set, skill_names(skill_set))
            skill_set, names = skill_cache[skill_set_ref]
            require(skill_set.get("scenario") == scenario, errors, sample_id, "skill set scenario does not match sample scenario")
            validate_invocation(row.get("candidate_invocation"), errors, sample_id, "candidate_invocation", names)
            fallback = row.get("fallback_invocation")
            if decision == "Fallback":
                require(fallback is not None, errors, sample_id, "Fallback samples require fallback_invocation")
                validate_invocation(fallback, errors, sample_id, "fallback_invocation", names)
            elif fallback is not None:
                validate_invocation(fallback, errors, sample_id, "fallback_invocation", names)
        else:
            errors.append(f"{sample_id}: skill_set_ref must be a string")

    for group_id, decisions in groups.items():
        unique = set(decisions)
        if group_id and len(decisions) >= 2 and len(unique) < 2:
            errors.append(f"{group_id}: contrast group has no decision contrast")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate AuthSkillBench JSONL samples.")
    parser.add_argument("dataset", type=Path)
    args = parser.parse_args()

    errors = validate_dataset(args.dataset)
    if errors:
        print(f"Validation failed with {len(errors)} error(s):")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"Validation passed: {args.dataset}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
