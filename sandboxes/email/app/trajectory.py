from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from .api import DEFAULT_STATE_PATH, TOOLKIT_SPEC, TOOL_SPECS
from .benchmark import (
    DEFAULT_CANDIDATE_FIXTURES_DIR,
    DEFAULT_CONTRAST_GROUPS_DIR,
    DEFAULT_ENVIRONMENTS_DIR,
    DEFAULT_SKILLS_DIR,
    DEFAULT_TASK_VARIANTS_DIR,
    compose_case_from_variant,
    iter_case_specs,
)
from .runtime import EmailSandbox


DEFAULT_TRAJECTORIES_DIR = Path(__file__).resolve().parents[1] / "data" / "trajectories"


def _trajectory_step(phase: str, entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "phase": phase,
        "tool": entry["tool"],
        "arguments": entry["arguments"],
        "result": entry["result"],
    }


def build_fixture_trajectory(
    group: dict[str, Any],
    variant: dict[str, Any],
    state_path: Path = DEFAULT_STATE_PATH,
    environments_dir: Path = DEFAULT_ENVIRONMENTS_DIR,
    task_variants_dir: Path = DEFAULT_TASK_VARIANTS_DIR,
    candidate_fixtures_dir: Path = DEFAULT_CANDIDATE_FIXTURES_DIR,
    skills_dir: Path = DEFAULT_SKILLS_DIR,
) -> dict[str, Any]:
    case = compose_case_from_variant(
        group,
        variant,
        environments_dir=environments_dir,
        task_variants_dir=task_variants_dir,
        candidate_fixtures_dir=candidate_fixtures_dir,
        skills_dir=skills_dir,
    )

    sandbox = EmailSandbox.load(state_path)
    sandbox.apply_environment_profile(case.get("environment_profile"))
    environment, observations = sandbox.build_environment(case.get("observation_refs", []))
    observation_trace = copy.deepcopy(sandbox.trace)
    candidate_result = sandbox.run_invocation(case["candidate_invocation"], apply=False)
    candidate_trace = copy.deepcopy(sandbox.trace[len(observation_trace) :])

    return {
        "schema_version": "authskillbench.email_trajectory.v1",
        "trajectory_id": f"{case['case_id']}.fixture_replay",
        "source": "fixture_replay",
        "case_id": case["case_id"],
        "contrast_group_id": case["contrast_group_id"],
        "trusted_skill_ref": case["trusted_skill_ref"],
        "skill_under_test": case["skill_under_test"],
        "trusted_skill": case["trusted_skill"],
        "task": case["task"],
        "task_variant": case["task_variant"],
        "environment_profile": case["environment_profile"],
        "agent_visible_input": {
            "task": case["task"],
            "environment": environment,
            "tools": TOOL_SPECS,
            "toolkit": {
                "toolkit_id": TOOLKIT_SPEC.get("toolkit_id"),
                "name_for_model": TOOLKIT_SPEC.get("name_for_model"),
                "description_for_model": TOOLKIT_SPEC.get("description_for_model"),
            },
        },
        "agent_observations": [
            {"ref": item["ref"], "visible": item["visible"]}
            for item in observations
        ],
        "steps": [
            *[_trajectory_step("context_observation", entry) for entry in observation_trace],
            *[_trajectory_step("candidate_invocation", entry) for entry in candidate_trace],
        ],
        "candidate_invocation": case["candidate_invocation"],
        "candidate_result": candidate_result,
        "runtime_metadata": {
            "environment_snapshot_id": sandbox.state.get("snapshot_id"),
            "applied_environment_overlays": sandbox.state.get("applied_environment_overlays", []),
            "candidate_apply_side_effects": False,
        },
    }


def generate_trajectories(
    selected: list[str] | None = None,
    state_path: Path = DEFAULT_STATE_PATH,
    contrast_groups_dir: Path = DEFAULT_CONTRAST_GROUPS_DIR,
    environments_dir: Path = DEFAULT_ENVIRONMENTS_DIR,
    task_variants_dir: Path = DEFAULT_TASK_VARIANTS_DIR,
    candidate_fixtures_dir: Path = DEFAULT_CANDIDATE_FIXTURES_DIR,
    skills_dir: Path = DEFAULT_SKILLS_DIR,
) -> list[dict[str, Any]]:
    trajectories: list[dict[str, Any]] = []
    for group, variant in iter_case_specs(contrast_groups_dir=contrast_groups_dir, selected=selected):
        trajectories.append(
            build_fixture_trajectory(
                group,
                variant,
                state_path=state_path,
                environments_dir=environments_dir,
                task_variants_dir=task_variants_dir,
                candidate_fixtures_dir=candidate_fixtures_dir,
                skills_dir=skills_dir,
            )
        )
    return trajectories


def write_trajectory_files(trajectories: list[dict[str, Any]], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for trajectory in trajectories:
        trajectory_id = str(trajectory.get("trajectory_id") or trajectory["case_id"])
        output_path = output_dir / f"{trajectory_id}.trajectory.json"
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(trajectory, f, indent=2, sort_keys=False)
            f.write("\n")
