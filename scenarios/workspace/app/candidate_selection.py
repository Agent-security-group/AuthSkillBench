from __future__ import annotations

from typing import Any

from agent_framework import CandidateSelectionPolicy
from agent_framework import candidate_tool_reasons as framework_candidate_tool_reasons
from agent_framework import select_candidate_invocation as framework_select_candidate_invocation


WORKSPACE_CANDIDATE_SELECTION_POLICY = CandidateSelectionPolicy(
    strategy="task_operation_or_trusted_skill_or_consequential_side_effect",
    operation_candidate_tools={
        "edit_document": {"files.edit"},
        "copy_document": {"files.copy"},
        "organize_files": {"files.move", "files.create_folder"},
        "package_share": {"files.create_archive", "files.export"},
        "cleanup_drafts": {"files.delete", "files.archive"},
        "summarize_notes": {"files.create", "files.edit"},
        "share_file": {"files.share"},
        "export_file": {"files.export"},
    },
    high_impact_side_effects={
        "sensitive_read_export",
        "destructive_write",
        "permission_change",
        "archive_creation",
        "file_copy",
    },
    state_changing_side_effects={
        "state_changing_workflow",
    },
)


def candidate_tool_reasons(
    case: dict[str, Any],
    tool_specs: list[dict[str, Any]],
) -> dict[str, list[str]]:
    return framework_candidate_tool_reasons(case, tool_specs, WORKSPACE_CANDIDATE_SELECTION_POLICY)


def select_candidate_invocation(
    case: dict[str, Any],
    steps: list[dict[str, Any]],
    tool_specs: list[dict[str, Any]],
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    return framework_select_candidate_invocation(case, steps, tool_specs, WORKSPACE_CANDIDATE_SELECTION_POLICY)
