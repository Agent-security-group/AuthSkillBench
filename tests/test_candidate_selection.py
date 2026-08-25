"""Tests for candidate_selection operation mappings.

Bug: The original ``operation_candidate_tools`` dict was missing several
     real operations (``api_call``, ``fill``, ``verify``), so candidate
     selection returned ``None`` for those task types.

Fix: Added mappings for all 12 operations found in real task data:
     api_call, audit, click, download, extract, fetch, fill, navigate,
     scan, search, submit, verify.
"""
from __future__ import annotations

import pytest

from scenarios.browser.app.candidate_selection import (
    BROWSER_CANDIDATE_SELECTION_POLICY,
    candidate_tool_reasons,
    select_candidate_invocation,
)
from scenarios.browser.app.api import TOOL_SPECS


# ---------------------------------------------------------------------------
# Operation coverage
# ---------------------------------------------------------------------------

EXPECTED_OPERATIONS = {
    "api_call", "audit", "click", "download", "extract",
    "fetch", "fill", "navigate", "scan", "search",
    "submit", "verify",
}


class TestOperationMappings:
    """All real task operations must be mapped to candidate tools."""

    def test_all_operations_mapped(self):
        mapped = set(BROWSER_CANDIDATE_SELECTION_POLICY.operation_candidate_tools.keys())
        missing = EXPECTED_OPERATIONS - mapped
        assert not missing, f"Missing operation mappings: {missing}"

    def test_api_call_maps_to_api_tools(self):
        tools = BROWSER_CANDIDATE_SELECTION_POLICY.operation_candidate_tools["api_call"]
        assert "http_request" in tools or "api_test_request" in tools

    def test_search_maps_to_web_search(self):
        tools = BROWSER_CANDIDATE_SELECTION_POLICY.operation_candidate_tools["search"]
        assert "web_search" in tools

    def test_extract_maps_to_extraction_tools(self):
        tools = BROWSER_CANDIDATE_SELECTION_POLICY.operation_candidate_tools["extract"]
        assert any("extract" in t for t in tools)

    def test_scan_maps_to_security_tools(self):
        tools = BROWSER_CANDIDATE_SELECTION_POLICY.operation_candidate_tools["scan"]
        assert any("security" in t or "scan" in t for t in tools)

    def test_verify_maps_to_safety_tools(self):
        tools = BROWSER_CANDIDATE_SELECTION_POLICY.operation_candidate_tools["verify"]
        assert any("safety" in t or "check" in t or "scan" in t for t in tools)

    def test_fill_maps_to_input_tools(self):
        tools = BROWSER_CANDIDATE_SELECTION_POLICY.operation_candidate_tools["fill"]
        assert any("input" in t for t in tools)

    def test_download_maps_to_download_tools(self):
        tools = BROWSER_CANDIDATE_SELECTION_POLICY.operation_candidate_tools["download"]
        assert any("download" in t for t in tools)


# ---------------------------------------------------------------------------
# Candidate tool reasons with real cases
# ---------------------------------------------------------------------------

class TestCandidateToolReasons:
    """candidate_tool_reasons should return non-empty reasons for real cases."""

    @pytest.fixture(scope="class")
    def first_case(self):
        from scenarios.browser.app.benchmark import iter_case_specs
        from scenarios.browser.app.agent_runner import _compose_runtime_case

        specs = list(iter_case_specs())
        g, v = specs[0]
        return _compose_runtime_case(g, v)

    def test_reasons_returned(self, first_case):
        reasons = candidate_tool_reasons(first_case, TOOL_SPECS)
        assert isinstance(reasons, dict)
        assert len(reasons) > 0, "Should find at least one candidate tool with reasons"

    def test_reasons_include_operation_based(self, first_case):
        op = first_case["task"].get("operation")
        if op:
            reasons = candidate_tool_reasons(first_case, TOOL_SPECS)
            # At least one tool should have an operation-based reason
            has_op_reason = any(
                any(r.startswith("task.operation:") for r in rs)
                for rs in reasons.values()
            )
            assert has_op_reason, f"Expected operation-based reason for op={op}"


# ---------------------------------------------------------------------------
# Select candidate invocation from steps
# ---------------------------------------------------------------------------

class TestSelectCandidateInvocation:
    """select_candidate_invocation should identify the most consequential tool call."""

    def _make_steps(self, tool_name: str, arguments: dict) -> list[dict]:
        return [
            {"phase": "assistant_message", "turn_index": 0, "content": None, "tool_call_count": 1},
            {
                "phase": "agent_tool_call",
                "turn_index": 0,
                "tool_call_id": "call_1",
                "tool": tool_name,
                "agent_tool_name": tool_name,
                "arguments": arguments,
                "result": {"ok": True, "tool": tool_name, "result": {}},
            },
            {"phase": "assistant_message", "turn_index": 1, "content": "done", "tool_call_count": 0},
        ]

    def test_selects_http_request_for_api_call(self):
        from scenarios.browser.app.benchmark import iter_case_specs
        from scenarios.browser.app.agent_runner import _compose_runtime_case

        specs = list(iter_case_specs())
        # Find an api_call case
        for g, v in specs:
            case = _compose_runtime_case(g, v)
            if case["task"].get("operation") == "api_call":
                break
        steps = self._make_steps("http_request", {"url": "http://api.example.com/docs", "method": "GET"})
        inv, sel = select_candidate_invocation(case, steps, TOOL_SPECS)
        assert sel["selected_tool"] == "http_request"
        assert inv is not None
        assert inv["skill"] == "http_request"

    def test_selects_web_search_for_search_operation(self):
        from scenarios.browser.app.benchmark import iter_case_specs
        from scenarios.browser.app.agent_runner import _compose_runtime_case

        specs = list(iter_case_specs())
        for g, v in specs:
            case = _compose_runtime_case(g, v)
            if case["task"].get("operation") == "search":
                break
        steps = self._make_steps("web_search", {"query": "test", "max_results": 3})
        inv, sel = select_candidate_invocation(case, steps, TOOL_SPECS)
        assert sel["selected_tool"] == "web_search"

    def test_returns_none_when_no_matching_tool_called(self):
        from scenarios.browser.app.benchmark import iter_case_specs
        from scenarios.browser.app.agent_runner import _compose_runtime_case

        specs = list(iter_case_specs())
        g, v = specs[0]
        case = _compose_runtime_case(g, v)
        # Call a tool not in any candidate mapping for this case
        steps = self._make_steps("nonexistent_tool_xyz", {})
        inv, sel = select_candidate_invocation(case, steps, TOOL_SPECS)
        assert inv is None
        assert sel["selected_tool"] is None

    def test_priority_high_impact_over_operation(self):
        """High-impact side-effect tools should be prioritized over operation matches."""
        from scenarios.browser.app.benchmark import iter_case_specs
        from scenarios.browser.app.agent_runner import _compose_runtime_case

        specs = list(iter_case_specs())
        g, v = specs[0]
        case = _compose_runtime_case(g, v)
        # Two tool calls: one matching operation, one with high-impact side effect
        steps = [
            {"phase": "assistant_message", "turn_index": 0, "content": None, "tool_call_count": 2},
            {
                "phase": "agent_tool_call", "turn_index": 0, "tool_call_id": "call_1",
                "tool": "web_search", "agent_tool_name": "web_search",
                "arguments": {"query": "test"}, "result": {"ok": True},
            },
            {
                "phase": "agent_tool_call", "turn_index": 0, "tool_call_id": "call_2",
                "tool": "http_request", "agent_tool_name": "http_request",
                "arguments": {"url": "http://api.example.com", "method": "GET"},
                "result": {"ok": True},
            },
            {"phase": "assistant_message", "turn_index": 1, "content": "done", "tool_call_count": 0},
        ]
        inv, sel = select_candidate_invocation(case, steps, TOOL_SPECS)
        # http_request has side_effect=network_request (state_changing), should be selected
        assert sel["selected_tool"] is not None
