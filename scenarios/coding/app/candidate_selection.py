from __future__ import annotations

from typing import Any

from agent_framework import CandidateSelectionPolicy
from agent_framework import candidate_tool_reasons as framework_candidate_tool_reasons
from agent_framework import select_candidate_invocation as framework_select_candidate_invocation


CODING_CANDIDATE_SELECTION_POLICY = CandidateSelectionPolicy(
    strategy="task_operation_or_trusted_skill_or_consequential_side_effect",
    operation_candidate_tools={
        "approve_pr": {"pr.approve"},
        "merge_pr": {"pr.merge"},
    },
    high_impact_side_effects={
        "approve_pr",
        "merge_pr",
    },
    state_changing_side_effects={
        "state_changing_workflow",
    },
)


def candidate_tool_reasons(
    case: dict[str, Any],
    tool_specs: list[dict[str, Any]],
) -> dict[str, list[str]]:
    return framework_candidate_tool_reasons(case, tool_specs, CODING_CANDIDATE_SELECTION_POLICY)


def select_candidate_invocation(
    case: dict[str, Any],
    steps: list[dict[str, Any]],
    tool_specs: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    return framework_select_candidate_invocation(case, steps, tool_specs, CODING_CANDIDATE_SELECTION_POLICY)
