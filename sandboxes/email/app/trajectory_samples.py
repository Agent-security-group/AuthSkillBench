from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .api import DEFAULT_STATE_PATH
from .oracle import build_sample
from .runtime import EmailSandbox


def read_trajectory(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        trajectory = json.load(f)
    if not isinstance(trajectory, dict):
        raise ValueError(f"trajectory must be a JSON object: {path}")
    return trajectory


def _case_from_trajectory(trajectory: dict[str, Any]) -> dict[str, Any]:
    candidate = trajectory.get("candidate_invocation")
    if not isinstance(candidate, dict):
        raise ValueError(f"{trajectory.get('trajectory_id', '<unknown>')}: candidate_invocation is null")
    environment_profile = trajectory.get("environment_profile")
    if not isinstance(environment_profile, dict):
        raise ValueError(f"{trajectory.get('trajectory_id', '<unknown>')}: environment_profile is missing")
    task = trajectory.get("task")
    if not isinstance(task, dict):
        raise ValueError(f"{trajectory.get('trajectory_id', '<unknown>')}: task is missing")
    return {
        "case_id": trajectory["case_id"],
        "scenario": trajectory.get("scenario", "email_communication_agent"),
        "contrast_group_id": trajectory["contrast_group_id"],
        "trusted_skill_ref": trajectory.get("trusted_skill_ref"),
        "skill_under_test": trajectory.get("skill_under_test"),
        "trusted_skill": trajectory.get("trusted_skill"),
        "task": task,
        "task_variant": trajectory.get("task_variant"),
        "environment_profile_ref": environment_profile.get("environment_profile_id"),
        "environment_type": environment_profile["environment_type"],
        "environment_profile": environment_profile,
        "observation_refs": environment_profile.get("observation_refs", []),
        "candidate_invocation": candidate,
    }


def sample_from_trajectory(
    trajectory: dict[str, Any],
    state_path: Path = DEFAULT_STATE_PATH,
) -> dict[str, Any]:
    sample = build_sample(EmailSandbox.load(state_path), _case_from_trajectory(trajectory))
    sample["sample_id"] = f"{sample['sample_id']}__{trajectory.get('source', 'trajectory')}"
    sample["hidden_metadata"]["trajectory_id"] = trajectory.get("trajectory_id")
    sample["hidden_metadata"]["trajectory_source"] = trajectory.get("source")
    sample["hidden_metadata"]["trajectory_model"] = trajectory.get("model")
    return sample


def samples_from_trajectory_paths(
    paths: list[Path],
    state_path: Path = DEFAULT_STATE_PATH,
    skip_without_candidate: bool = True,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    samples: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for path in paths:
        trajectory = read_trajectory(path)
        if not isinstance(trajectory.get("candidate_invocation"), dict):
            skipped.append(
                {
                    "path": str(path),
                    "trajectory_id": trajectory.get("trajectory_id"),
                    "reason": "missing_candidate_invocation",
                }
            )
            if skip_without_candidate:
                continue
        samples.append(sample_from_trajectory(trajectory, state_path=state_path))
    return samples, skipped


def iter_trajectory_paths(inputs: list[Path]) -> list[Path]:
    paths: list[Path] = []
    for item in inputs:
        if item.is_dir():
            paths.extend(sorted(item.glob("*.trajectory.json")))
            paths.extend(sorted(item.glob("*.json")))
        else:
            paths.append(item)
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in paths:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append(path)
    return unique
