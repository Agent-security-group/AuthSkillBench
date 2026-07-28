from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CandidateSelectionPolicy:
    strategy: str
    operation_candidate_tools: dict[str, set[str]] = field(default_factory=dict)
    high_impact_side_effects: set[str] = field(default_factory=set)
    state_changing_side_effects: set[str] = field(default_factory=set)


def candidate_invocation_from_step(step: dict[str, Any]) -> dict[str, Any]:
    return {
        "skill": step["tool"],
        "arguments": copy.deepcopy(step["arguments"]),
        "claimed_reason": "Captured from an agent tool call.",
    }


def tool_specs_by_name(tool_specs: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(spec["name"]): spec for spec in tool_specs}


def operation_for_case(case: dict[str, Any]) -> str | None:
    for source in (case.get("task_variant"), case.get("task")):
        if isinstance(source, dict) and isinstance(source.get("operation"), str):
            return source["operation"]
    return None


def candidate_tool_reasons(
    case: dict[str, Any],
    tool_specs: list[dict[str, Any]],
    policy: CandidateSelectionPolicy,
) -> dict[str, list[str]]:
    reasons: dict[str, list[str]] = {}
    specs_by_name = tool_specs_by_name(tool_specs)

    def add(tool: str, reason: str) -> None:
        if tool not in specs_by_name:
            return
        reasons.setdefault(tool, [])
        if reason not in reasons[tool]:
            reasons[tool].append(reason)

    operation = operation_for_case(case)
    if operation:
        for tool in policy.operation_candidate_tools.get(operation, set()):
            add(tool, f"task.operation:{operation}")

    trusted_skill = case.get("trusted_skill")
    if isinstance(trusted_skill, dict):
        for tool in trusted_skill.get("mapped_tools", []):
            if isinstance(tool, str):
                add(tool, "trusted_skill.mapped_tools")

    for tool, spec in specs_by_name.items():
        side_effect = spec.get("side_effect")
        if side_effect in policy.high_impact_side_effects or side_effect in policy.state_changing_side_effects:
            add(tool, f"tool.side_effect:{side_effect}")

    return reasons


def _candidate_priority(
    tool: str,
    reasons: list[str],
    specs_by_name: dict[str, dict[str, Any]],
    policy: CandidateSelectionPolicy,
) -> int:
    side_effect = specs_by_name.get(tool, {}).get("side_effect")
    if side_effect in policy.high_impact_side_effects:
        return 0
    if any(reason.startswith("task.operation:") for reason in reasons):
        return 1
    if "trusted_skill.mapped_tools" in reasons:
        return 2
    if side_effect in policy.state_changing_side_effects:
        return 3
    return 4


def select_candidate_invocation(
    case: dict[str, Any],
    steps: list[dict[str, Any]],
    tool_specs: list[dict[str, Any]],
    policy: CandidateSelectionPolicy,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Select the most consequential agent tool call for candidate recording."""

    reasons_by_tool = candidate_tool_reasons(case, tool_specs, policy)
    specs_by_name = tool_specs_by_name(tool_specs)
    ranked_steps: list[tuple[int, int, dict[str, Any]]] = []
    for step_index, step in enumerate(steps):
        tool = step.get("tool")
        if step.get("phase") != "agent_tool_call" or not isinstance(tool, str):
            continue
        reasons = reasons_by_tool.get(tool)
        if not reasons:
            continue
        ranked_steps.append((_candidate_priority(tool, reasons, specs_by_name, policy), step_index, step))

    if not ranked_steps:
        return None, {
            "strategy": policy.strategy,
            "selected_tool": None,
            "candidate_tool_names": sorted(reasons_by_tool),
        }

    _priority, step_index, selected_step = min(ranked_steps, key=lambda item: (item[0], item[1]))
    selected_tool = selected_step["tool"]
    return candidate_invocation_from_step(selected_step), {
        "strategy": policy.strategy,
        "selected_tool": selected_tool,
        "selected_step_index": step_index,
        "selected_reasons": reasons_by_tool.get(selected_tool, []),
        "candidate_tool_names": sorted(reasons_by_tool),
    }
