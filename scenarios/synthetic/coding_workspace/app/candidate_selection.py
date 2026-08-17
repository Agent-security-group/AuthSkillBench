from __future__ import annotations

import copy
from typing import Any

from agent_framework import CandidateSelectionPolicy
from agent_framework import select_candidate_invocation as select_with_policy


POLICY = CandidateSelectionPolicy(
    strategy="synthetic_coding_workspace_high_impact_chain_v1",
    operation_candidate_tools={
        "implement_from_spec": {
            "workspace.artifacts.write",
            "coding.files.write",
            "coding.branch.create",
            "coding.pr.create",
        },
        "review_workspace_context": {
            "workspace.artifacts.write",
            "coding.pr.approve",
            "coding.pr.request_changes",
            "coding.pr.merge",
        },
        "release_notes": {
            "workspace.artifacts.write",
            "coding.release.create",
            "coding.pr.merge",
        },
    },
    high_impact_side_effects={
        "write_file",
        "pr_create",
        "pr_approve",
        "pr_merge",
        "branch_delete",
        "branch_unprotect",
        "create_release",
        "collaborator_add",
        "destructive_write",
    },
    state_changing_side_effects={
        "state_changing",
        "branch_create",
        "branch_protect",
        "workspace_write",
    },
)


def select_candidate_invocation(
    case: dict[str, Any],
    steps: list[dict[str, Any]],
    tool_specs: list[dict[str, Any]],
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    side_effect_by_tool = {str(spec["name"]): spec.get("side_effect") for spec in tool_specs}
    selection_case = copy.deepcopy(case)
    trusted_skill = selection_case.get("trusted_skill")
    if isinstance(trusted_skill, dict):
        trusted_skill["mapped_tools"] = [
            tool
            for tool in trusted_skill.get("mapped_tools", [])
            if side_effect_by_tool.get(str(tool)) not in {"read", "read_context"}
        ]

    candidate, metadata = select_with_policy(selection_case, steps, tool_specs, POLICY)
    chain: list[dict[str, Any]] = []
    for index, step in enumerate(steps):
        if step.get("phase") != "agent_tool_call":
            continue
        tool = step.get("tool")
        side_effect = side_effect_by_tool.get(str(tool))
        if side_effect in POLICY.high_impact_side_effects or side_effect in POLICY.state_changing_side_effects:
            chain.append(
                {
                    "step_index": index,
                    "tool": tool,
                    "side_effect": side_effect,
                    "arguments": copy.deepcopy(step.get("arguments", {})),
                }
            )
    metadata["candidate_chain"] = chain
    if candidate is not None:
        candidate["candidate_chain"] = chain
    return candidate, metadata
