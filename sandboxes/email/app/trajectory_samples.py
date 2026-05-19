from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_trajectory(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        trajectory = json.load(f)
    if not isinstance(trajectory, dict):
        raise ValueError(f"trajectory must be a JSON object: {path}")
    return trajectory


def candidate_record_from_trajectory(trajectory: dict[str, Any]) -> dict[str, Any]:
    candidate = trajectory.get("candidate_invocation")
    if not isinstance(candidate, dict):
        raise ValueError(f"{trajectory.get('trajectory_id', '<unknown>')}: candidate_invocation is null")
    return {
        "record_id": f"{trajectory['case_id']}__{trajectory.get('source', 'trajectory')}",
        "schema_version": "authskillbench.email_candidate_record.v1",
        "source": trajectory.get("source"),
        "model": trajectory.get("model"),
        "case_id": trajectory["case_id"],
        "contrast_group_id": trajectory["contrast_group_id"],
        "task": trajectory.get("task"),
        "task_variant": trajectory.get("task_variant"),
        "environment_profile": trajectory.get("environment_profile"),
        "candidate_invocation": candidate,
        "candidate_result": trajectory.get("candidate_result"),
        "runtime_metadata": trajectory.get("runtime_metadata", {}),
    }


def candidate_records_from_trajectory_paths(
    paths: list[Path],
    skip_without_candidate: bool = True,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    records: list[dict[str, Any]] = []
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
        records.append(candidate_record_from_trajectory(trajectory))
    return records, skipped


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
