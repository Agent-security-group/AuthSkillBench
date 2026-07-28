from __future__ import annotations

from typing import Any

from agent_framework import CandidateSelectionPolicy
from agent_framework import candidate_tool_reasons as framework_candidate_tool_reasons
from agent_framework import select_candidate_invocation as framework_select_candidate_invocation


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
    },
)


def candidate_tool_reasons(
    case: dict[str, Any],
    tool_specs: list[dict[str, Any]],
) -> dict[str, list[str]]:
    return framework_candidate_tool_reasons(case, tool_specs, BROWSER_CANDIDATE_SELECTION_POLICY)


def select_candidate_invocation(
    case: dict[str, Any],
    steps: list[dict[str, Any]],
    tool_specs: list[dict[str, Any]],
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    return framework_select_candidate_invocation(case, steps, tool_specs, BROWSER_CANDIDATE_SELECTION_POLICY)
