"""Tests for the agent_runner LLM-driven tool-calling flow.

Covers:
  - Case composition (_compose_runtime_case)
  - Message building (build_initial_messages)
  - Full agent loop with a mock LLM client
  - Trajectory write + read-back
  - __init__.py lazy exports
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scenarios.browser.app.mock_web_server import ScenarioWebServer


@pytest.fixture(autouse=True)
def _clean_servers():
    ScenarioWebServer.shutdown_all()
    yield
    ScenarioWebServer.shutdown_all()


# ---------------------------------------------------------------------------
# Case composition
# ---------------------------------------------------------------------------

class TestComposeRuntimeCase:
    """_compose_runtime_case should assemble all case components."""

    def test_returns_dict_with_required_keys(self):
        from scenarios.browser.app.benchmark import iter_case_specs
        from scenarios.browser.app.agent_runner import _compose_runtime_case

        specs = list(iter_case_specs())
        g, v = specs[0]
        case = _compose_runtime_case(g, v)
        required = {"case_id", "task", "trusted_skill", "threat_profile", "task_variant"}
        assert required.issubset(case.keys())

    def test_case_id_matches_variant(self):
        from scenarios.browser.app.benchmark import iter_case_specs
        from scenarios.browser.app.agent_runner import _compose_runtime_case

        specs = list(iter_case_specs())
        g, v = specs[0]
        case = _compose_runtime_case(g, v)
        assert case["case_id"] == v["case_id"]

    def test_task_has_operation(self):
        from scenarios.browser.app.benchmark import iter_case_specs
        from scenarios.browser.app.agent_runner import _compose_runtime_case

        specs = list(iter_case_specs())
        for g, v in specs:
            case = _compose_runtime_case(g, v)
            assert "operation" in case["task"], f"Missing operation for {case['case_id']}"

    def test_all_90_cases_compose(self):
        from scenarios.browser.app.benchmark import iter_case_specs
        from scenarios.browser.app.agent_runner import _compose_runtime_case

        specs = list(iter_case_specs())
        assert len(specs) == 90
        for g, v in specs:
            case = _compose_runtime_case(g, v)
            assert case["case_id"], "case_id should be non-empty"


# ---------------------------------------------------------------------------
# Message building
# ---------------------------------------------------------------------------

class TestBuildInitialMessages:
    """build_initial_messages should produce system + user messages."""

    def test_returns_two_messages(self):
        from scenarios.browser.app.benchmark import iter_case_specs
        from scenarios.browser.app.agent_runner import _compose_runtime_case, build_initial_messages

        specs = list(iter_case_specs())
        g, v = specs[0]
        case = _compose_runtime_case(g, v)
        messages = build_initial_messages(case)
        assert len(messages) == 2

    def test_first_is_system(self):
        from scenarios.browser.app.benchmark import iter_case_specs
        from scenarios.browser.app.agent_runner import _compose_runtime_case, build_initial_messages

        specs = list(iter_case_specs())
        g, v = specs[0]
        case = _compose_runtime_case(g, v)
        messages = build_initial_messages(case)
        assert messages[0]["role"] == "system"
        assert len(messages[0]["content"]) > 50

    def test_second_is_user_with_json(self):
        from scenarios.browser.app.benchmark import iter_case_specs
        from scenarios.browser.app.agent_runner import _compose_runtime_case, build_initial_messages

        specs = list(iter_case_specs())
        g, v = specs[0]
        case = _compose_runtime_case(g, v)
        messages = build_initial_messages(case)
        assert messages[1]["role"] == "user"
        # User message should be valid JSON
        payload = json.loads(messages[1]["content"])
        assert "task" in payload
        assert "toolkit" in payload


# ---------------------------------------------------------------------------
# Full agent loop with mock LLM
# ---------------------------------------------------------------------------

class _MockClient:
    """Minimal LLM client that simulates tool calls."""

    source = "unit_test"
    model = "mock-model"

    def __init__(self, tool_sequence: list[tuple[str, dict]] | None = None):
        self._sequence = tool_sequence or []
        self._index = 0

    def create(self, messages, tools):
        if self._index < len(self._sequence):
            tool_name, args = self._sequence[self._index]
            self._index += 1
            return {
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [{
                            "id": f"call_{self._index}",
                            "type": "function",
                            "function": {
                                "name": tool_name,
                                "arguments": json.dumps(args),
                            },
                        }],
                    }
                }]
            }
        return {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": "Task completed successfully.",
                }
            }]
        }


class TestAgentRunnerFlow:
    """Full agent loop with mock LLM client."""

    @pytest.fixture
    def case(self):
        from scenarios.browser.app.benchmark import iter_case_specs
        from scenarios.browser.app.agent_runner import _compose_runtime_case
        specs = list(iter_case_specs())
        g, v = specs[0]
        return _compose_runtime_case(g, v)

    def test_two_tool_calls_then_finish(self, case):
        from scenarios.browser.app.agent_runner import build_initial_messages
        from scenarios.browser.app.api import BrowserScenarioAPI, TOOL_SPECS
        from agent_framework import ToolCallingAgentRunner, openai_tools_from_specs

        messages = build_initial_messages(case)
        client = _MockClient([
            ("web_search", {"query": "api documentation", "max_results": 3}),
            ("fetch_url", {"url": "http://api.example.com/docs", "include_html": True}),
        ])
        api = BrowserScenarioAPI(apply_side_effects=False)
        runner = ToolCallingAgentRunner(
            client=client, tools=openai_tools_from_specs(TOOL_SPECS),
            invoke_tool=api.invoke, max_turns=8,
        )
        steps, final_message, _ = runner.run(messages)

        # Should have: assistant, tool_call, assistant, tool_call, assistant = 5 steps
        assert len(steps) == 5
        assert final_message is not None
        assert final_message.get("content") == "Task completed successfully."

        # Verify all tool calls succeeded
        tool_calls = [s for s in steps if s["phase"] == "agent_tool_call"]
        assert len(tool_calls) == 2
        assert all(tc["result"]["ok"] for tc in tool_calls)

    def test_no_tool_calls_just_answer(self, case):
        from scenarios.browser.app.agent_runner import build_initial_messages
        from scenarios.browser.app.api import BrowserScenarioAPI, TOOL_SPECS
        from agent_framework import ToolCallingAgentRunner, openai_tools_from_specs

        messages = build_initial_messages(case)
        client = _MockClient([])  # No tool calls, immediate answer
        api = BrowserScenarioAPI(apply_side_effects=False)
        runner = ToolCallingAgentRunner(
            client=client, tools=openai_tools_from_specs(TOOL_SPECS),
            invoke_tool=api.invoke, max_turns=8,
        )
        steps, final_message, _ = runner.run(messages)

        assert len(steps) == 1
        assert steps[0]["phase"] == "assistant_message"
        assert steps[0]["tool_call_count"] == 0

    def test_max_turns_limit(self, case):
        from scenarios.browser.app.agent_runner import build_initial_messages
        from scenarios.browser.app.api import BrowserScenarioAPI, TOOL_SPECS
        from agent_framework import ToolCallingAgentRunner, openai_tools_from_specs

        messages = build_initial_messages(case)
        # LLM keeps calling web_search forever
        client = _MockClient([("web_search", {"query": "test"})] * 100)
        api = BrowserScenarioAPI(apply_side_effects=False)
        runner = ToolCallingAgentRunner(
            client=client, tools=openai_tools_from_specs(TOOL_SPECS),
            invoke_tool=api.invoke, max_turns=3,
        )
        steps, final_message, _ = runner.run(messages)

        # 3 turns * (1 assistant + 1 tool_call) = 6 steps
        tool_calls = [s for s in steps if s["phase"] == "agent_tool_call"]
        assert len(tool_calls) == 3


# ---------------------------------------------------------------------------
# Trajectory write
# ---------------------------------------------------------------------------

class TestTrajectoryWrite:
    """Trajectory files should be written and re-readable."""

    def test_write_and_read_back(self, tmp_path: Path):
        from scenarios.browser.app.trajectory import write_trajectory_files

        trajectory = {
            "schema_version": "authskillbench.browser_trajectory.v1",
            "trajectory_id": "test_case.unit_test",
            "case_id": "test_case",
            "steps": [
                {"phase": "assistant_message", "turn_index": 0, "content": "hello"},
            ],
            "final_message": {"role": "assistant", "content": "done"},
        }
        write_trajectory_files([trajectory], tmp_path)
        traj_path = tmp_path / "test_case.unit_test.trajectory.json"
        assert traj_path.exists()
        saved = json.loads(traj_path.read_text(encoding="utf-8"))
        assert saved["trajectory_id"] == "test_case.unit_test"
        assert len(saved["steps"]) == 1

    def test_write_multiple(self, tmp_path: Path):
        from scenarios.browser.app.trajectory import write_trajectory_files

        trajectories = [
            {"trajectory_id": f"case_{i}.test", "case_id": f"case_{i}", "steps": []}
            for i in range(3)
        ]
        write_trajectory_files(trajectories, tmp_path)
        for i in range(3):
            assert (tmp_path / f"case_{i}.test.trajectory.json").exists()


# ---------------------------------------------------------------------------
# __init__.py lazy exports
# ---------------------------------------------------------------------------

class TestInitExports:
    """__init__.py should lazily export all new modules."""

    def test_browser_scenario_api(self):
        from scenarios.browser.app import BrowserScenarioAPI
        assert BrowserScenarioAPI is not None

    def test_candidate_selection_policy(self):
        from scenarios.browser.app import BROWSER_CANDIDATE_SELECTION_POLICY
        assert BROWSER_CANDIDATE_SELECTION_POLICY.strategy.startswith("task_operation")

    def test_default_trajectories_dir(self):
        from scenarios.browser.app import DEFAULT_TRAJECTORIES_DIR
        assert DEFAULT_TRAJECTORIES_DIR.name == "trajectories"

    def test_run_live_agent_case(self):
        from scenarios.browser.app import run_live_agent_case
        assert callable(run_live_agent_case)

    def test_run_live_agent_cases(self):
        from scenarios.browser.app import run_live_agent_cases
        assert callable(run_live_agent_cases)

    def test_write_live_trajectories(self):
        from scenarios.browser.app import write_live_trajectories
        assert callable(write_live_trajectories)
