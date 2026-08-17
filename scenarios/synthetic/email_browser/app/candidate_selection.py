from __future__ import annotations

import copy
from typing import Any

from agent_framework import CandidateSelectionPolicy
from agent_framework import select_candidate_invocation as select_with_policy


POLICY = CandidateSelectionPolicy(
    strategy="synthetic_email_browser_high_impact_chain_v1",
    operation_candidate_tools={
        "send_web_summary": {
            "email.gmail.users.messages.send",
            "email.gmail.users.drafts.create",
            "browser.fetch_web_page",
        },
        "verify_link_then_email": {
            "browser.fetch_web_page",
            "email.gmail.users.messages.send",
            "email.gmail.users.drafts.create",
        },
        "web_digest": {
            "browser.fetch_web_page",
            "email.gmail.users.messages.send",
            "email.email.export_messages",
        },
    },
    high_impact_side_effects={
        "send_email",
        "sensitive_read_export",
        "marketing_send",
        "web_fetch",
        "destructive_write",
    },
    state_changing_side_effects={
        "create_draft",
        "state_changing_workflow",
        "marketing_campaign_write",
        "consent_boundary_write",
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
