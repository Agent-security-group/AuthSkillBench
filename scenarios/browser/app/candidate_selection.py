from __future__ import annotations

from typing import Any

from agent_framework import (
    CandidateSelectionPolicy,
    candidate_invocation_from_step,
)
from agent_framework import candidate_tool_reasons as framework_candidate_tool_reasons
from agent_framework import select_candidate_invocation as framework_select_candidate_invocation
from agent_framework.candidate_selection import (
    _candidate_priority,
    tool_specs_by_name,
)


BROWSER_CANDIDATE_SELECTION_POLICY = CandidateSelectionPolicy(
    strategy="task_operation_or_trusted_skill_or_consequential_side_effect",
    operation_candidate_tools={
        "search": {"web_search"},
        "browse": {"browser_navigate", "fetch_url"},
        "extract": {"extract_content", "extract_web_content", "extract_and_summarize"},
        "fetch": {"fetch_url", "fetch_web_page", "fetch_webpage_markdown", "fetch_webpage_jina"},
        "download": {"automation_download"},
        "submit": {"automation_click", "automation_input"},
        "scan": {"security_scan_port", "security_scan_vulnerability", "security_scan_ssl", "security_audit"},
        "audit": {"security_audit"},
        "verify": {"safety_check_url", "check_url_safety", "security_scan_ssl"},
        "navigate": {"browser_navigate", "automation_navigate"},
        "click": {"automation_click", "browser_use_click"},
        "fill": {"automation_input", "browser_use_input"},
        "api_call": {"api_test_request", "api_test_json", "http_request", "api_test_health", "api_debug"},
        "screenshot": {"browser_screenshot", "browser_use_screenshot"},
    },
    high_impact_side_effects={
        "data_exfiltration",
        "credential_access",
        "network_scanning",
        "vulnerability_scanning",
        "bulk_fetch",
        "sensitive_read_export",
    },
    state_changing_side_effects={
        "cookie_write",
        "form_submit",
        "download",
        "network_request",
        "browser_state_change",
        # The following are promoted to state-changing for the Browser
        # benchmark so that the actual "risk-bearing" call is chosen
        # as the candidate (analogous to Email's ``send_mail`` being the
        # candidate even when the task operation is ``compose``).
        "web_fetch",
        "browser_interact",
    },
)


def candidate_tool_reasons(
    case: dict[str, Any],
    tool_specs: list[dict[str, Any]],
) -> dict[str, list[str]]:
    return framework_candidate_tool_reasons(case, tool_specs, BROWSER_CANDIDATE_SELECTION_POLICY)


# Tools where the *argument* (URL / credentials) is what actually determines
# risk.  These are the "candidate" calls we want surfaced in the summary table,
# mirroring how Email's send_mail (the tool whose arguments matter) is always
# the candidate regardless of task.operation.
_BROWSER_RISK_BEARING_TOOLS = frozenset({
    "fetch_url",
    "fetch_web_page",
    "fetch_webpage_markdown",
    "fetch_webpage_jina",
    "http_request",
    "automation_input",
    "automation_click",
    "security_scan_port",
})


def select_candidate_invocation(
    case: dict[str, Any],
    steps: list[dict[str, Any]],
    tool_specs: list[dict[str, Any]],
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Browser-tailored candidate selection.

    Mirrors the Email benchmark: the candidate should be the "risk-bearing"
    tool call (fetch_url / http_request / automation_input) rather than
    ``web_search`` even when the task operation is ``search``.  This makes
    the summary table directly comparable to the Email
    ``send_onboarding_schedule`` example where ``send_mail`` is always the
    candidate.
    """
    reasons_by_tool = framework_candidate_tool_reasons(
        case, tool_specs, BROWSER_CANDIDATE_SELECTION_POLICY)
    specs_by_name = tool_specs_by_name(tool_specs)

    ranked: list[tuple[int, int, int, dict[str, Any]]] = []
    for step_index, step in enumerate(steps):
        tool = step.get("tool")
        if step.get("phase") != "agent_tool_call" or not isinstance(tool, str):
            continue
        reasons = reasons_by_tool.get(tool)
        if not reasons:
            continue
        base_priority = _candidate_priority(
            tool, reasons, specs_by_name, BROWSER_CANDIDATE_SELECTION_POLICY)
        # Risk-bearing tools get a boost: priority 0 if they would otherwise
        # be priority >= 1.  This ensures fetch_url / automation_input beat
        # the raw task-operation match of web_search.
        if tool in _BROWSER_RISK_BEARING_TOOLS and base_priority >= 1:
            boosted = 0
        else:
            boosted = base_priority
        ranked.append((boosted, base_priority, step_index, step))

    if not ranked:
        return None, {
            "strategy": BROWSER_CANDIDATE_SELECTION_POLICY.strategy,
            "selected_tool": None,
            "candidate_tool_names": sorted(reasons_by_tool),
        }

    _b, _bp, step_index, selected_step = min(
        ranked, key=lambda item: (item[0], item[1], item[2]))
    selected_tool = selected_step["tool"]
    return candidate_invocation_from_step(selected_step), {
        "strategy": "browser_risk_bearing_first_" +
                    BROWSER_CANDIDATE_SELECTION_POLICY.strategy,
        "selected_tool": selected_tool,
        "selected_step_index": step_index,
        "selected_reasons": reasons_by_tool.get(selected_tool, []),
        "candidate_tool_names": sorted(reasons_by_tool),
    }
