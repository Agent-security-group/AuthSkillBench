"""Extract candidate invocation records from workspace trajectory files for evaluation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .api import TOOL_SPECS
from .candidate_selection import select_candidate_invocation


def read_trajectory(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        trajectory = json.load(f)
    if not isinstance(trajectory, dict):
        raise ValueError(f"trajectory must be a JSON object: {path}")
    return trajectory


def candidate_record_from_trajectory(trajectory: dict[str, Any]) -> dict[str, Any]:
    """Extract a normalised candidate record from a trajectory dict.

    The record bundles the case context with the single tool invocation that the
    candidate-selection policy identified as the most consequential step.
    """
    candidate = _candidate_invocation_for_trajectory(trajectory)
    if not isinstance(candidate, dict):
        raise ValueError(
            f"{trajectory.get('trajectory_id', '<unknown>')}: "
            "candidate_invocation is null"
        )
    return {
        "record_id": f"{trajectory['case_id']}__{trajectory.get('source', 'trajectory')}",
        "schema_version": "authskillbench.workspace_candidate_record.v1",
        "source": trajectory.get("source"),
        "model": trajectory.get("model"),
        "case_id": trajectory["case_id"],
        "contrast_group_id": trajectory["contrast_group_id"],
        "task": trajectory.get("task"),
        "task_variant": trajectory.get("task_variant"),
        "threat_profile": trajectory.get("threat_profile"),
        "candidate_invocation": candidate,
        "candidate_result": trajectory.get("candidate_result"),
        "runtime_metadata": trajectory.get("runtime_metadata", {}),
    }


def _candidate_invocation_for_trajectory(trajectory: dict[str, Any]) -> dict[str, Any] | None:
    """Return the best-guess candidate invocation for a trajectory.

    If the trajectory already has a populated *candidate_invocation* field it is
    returned directly.  Otherwise the step list is re-scanned with the same
    selection policy used at runtime.
    """
    candidate = trajectory.get("candidate_invocation")
    if isinstance(candidate, dict):
        return candidate
    steps = trajectory.get("steps")
    if not isinstance(steps, list):
        return None
    agent_input = trajectory.get("agent_visible_input")
    embedded_tools = agent_input.get("tools") if isinstance(agent_input, dict) else None
    tool_specs = embedded_tools if isinstance(embedded_tools, list) else TOOL_SPECS
    derived_candidate, selection = select_candidate_invocation(trajectory, steps, tool_specs)
    if isinstance(derived_candidate, dict):
        trajectory["candidate_invocation"] = derived_candidate
        runtime_metadata = trajectory.setdefault("runtime_metadata", {})
        if isinstance(runtime_metadata, dict):
            runtime_metadata["candidate_selection"] = selection
            runtime_metadata["candidate_invocation_derived_from_steps"] = True
    return derived_candidate


def candidate_records_from_trajectory_paths(
    paths: list[Path],
    skip_without_candidate: bool = True,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Load trajectories from *paths* and extract candidate records.

    Returns ``(records, skipped)`` where *skipped* contains entries for
    trajectories that had no identifiable candidate invocation.
    """
    records: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for path in paths:
        trajectory = read_trajectory(path)
        if not isinstance(_candidate_invocation_for_trajectory(trajectory), dict):
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
    """Collect every trajectory JSON file from the given paths (files or directories).

    Duplicate resolved paths are deduplicated while preserving order.
    """
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
