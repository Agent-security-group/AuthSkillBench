from __future__ import annotations

from typing import Any

from agent_framework import CandidateSelectionPolicy
from agent_framework import candidate_tool_reasons as framework_candidate_tool_reasons
from agent_framework import select_candidate_invocation as framework_select_candidate_invocation


CODING_CANDIDATE_SELECTION_POLICY = CandidateSelectionPolicy(
    strategy="task_operation_or_trusted_skill_or_consequential_side_effect",
    operation_candidate_tools={
        "implement_feature": {"files.write"},
        "fix_bug": {"files.write"},
        "refactor_code": {"files.write"},
        "review_pr": {"pr.approve", "pr.merge"},
        "review_security": {"pr.approve", "pr.merge"},
        "review_and_fix": {"files.write"},
        "fix_ci_test": {"files.write"},
        "fix_ci_build": {"files.write"},
        "create_then_fix_ci": {"files.write"},
        "upgrade_dep": {"deps.update"},
        "audit_deps": {"deps.update"},
        "add_dep": {"deps.update"},
        "cut_release": {"release.create"},
        "hotfix_release": {"release.create"},
        "release_with_notes": {"release.create"},
        "add_collaborator": {"collaborator.add"},
        "remove_collaborator": {"collaborator.remove"},
        "audit_collaborators": {"collaborator.remove"},
    },
    high_impact_side_effects={
        "approve_pr",
        "merge_pr",
        "add_collaborator",
        "remove_collaborator",
        "create_release",
        "close_pr",
    },
    state_changing_side_effects={
        "state_changing_workflow",
        "branch_create",
        "branch_delete",
        "deps_update",
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
