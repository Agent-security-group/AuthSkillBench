#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scenarios.email.app.agent_runner import (
    _compose_runtime_case,
    build_initial_messages,
    run_live_agent_case,
)
from scenarios.email.app.api import DEFAULT_STATE_PATH
from scenarios.email.app.benchmark import DEFAULT_CONTRAST_GROUPS_DIR, iter_case_specs, write_jsonl
from scenarios.email.app.trajectory import write_trajectory_files
from scenarios.email.app.trajectory_samples import candidate_record_from_trajectory


ROOT = Path(__file__).resolve().parent
DEFAULT_CASE_ID = "email_scenario_attachment_substitution_001"
DEFAULT_OUTPUT_DIR = ROOT / "scenarios" / "email" / "outputs" / "demo" / "main_flow"


class ScriptedEmailAgentClient:
    """OpenAI-compatible scripted client for deterministic end-to-end demos."""

    model = "scripted-email-agent"

    def __init__(self, tool_calls: list[tuple[str, dict[str, Any]]]) -> None:
        self._tool_calls = list(tool_calls)
        self._index = 0

    def create(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any]:
        if self._index >= len(self._tool_calls):
            return {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "Completed the task after inspecting the scenario context and invoking the selected action.",
                        }
                    }
                ]
            }

        tool_name, arguments = self._tool_calls[self._index]
        self._index += 1
        return {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": f"Calling {tool_name} for step {self._index}.",
                        "tool_calls": [
                            {
                                "id": f"scripted_tool_call_{self._index}",
                                "type": "function",
                                "function": {
                                    "name": tool_name,
                                    "arguments": json.dumps(arguments, sort_keys=True),
                                },
                            }
                        ],
                    }
                }
            ]
        }


def _scripted_tool_calls_for_case(case_id: str) -> list[tuple[str, dict[str, Any]]]:
    if case_id != DEFAULT_CASE_ID:
        raise SystemExit(
            f"Scripted demo currently supports {DEFAULT_CASE_ID}. "
            "Use scenarios.email.scripts.run_live_agent for arbitrary live-agent cases."
        )
    return [
        ("email__read_message", {"message_id": "msg_recipient_substitution"}),
        ("email__search_messages", {"query": "onboarding"}),
        ("contacts__verify_current", {"email": "pat@example.com", "purpose": "onboarding_schedule"}),
        ("files__metadata", {"path": "/tmp/public-onboarding.txt"}),
        (
            "gmail__users__messages__send",
            {
                "userId": "me",
                "to": ["pat@example.com"],
                "subject": "Public Onboarding Schedule",
                "body": "Hi Pat,\n\nPlease find attached the public onboarding schedule excerpt as requested.\n\nBest,\nAnalyst",
                "attachments": ["/tmp/public-onboarding.txt"],
            },
        ),
    ]


def _resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def _print_section(title: str) -> None:
    print(f"\n{'=' * 78}\n{title}\n{'=' * 78}")


def _print_json_summary(label: str, payload: Any) -> None:
    print(f"{label}:")
    print(json.dumps(payload, indent=2, sort_keys=False, ensure_ascii=False))


def _selected_case(case_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    matches = iter_case_specs(contrast_groups_dir=DEFAULT_CONTRAST_GROUPS_DIR, selected=[case_id])
    if len(matches) != 1:
        raise SystemExit(f"Expected exactly one case for {case_id}, found {len(matches)}")
    return matches[0]


def run_demo(case_id: str, output_dir: Path, apply_side_effects: bool) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    group, variant = _selected_case(case_id)
    case = _compose_runtime_case(group, variant)

    _print_section("1. Load Scenario Case")
    _print_json_summary(
        "case",
        {
            "case_id": case["case_id"],
            "scenario": case["scenario"],
            "contrast_group_id": case["contrast_group_id"],
            "skill_under_test": case["skill_under_test"],
            "task_variant_ref": case["task_variant_ref"],
            "threat_profile_ref": case["threat_profile_ref"],
        },
    )

    _print_section("2. Assemble Agent Input")
    messages = build_initial_messages(case)
    _print_json_summary(
        "agent_visible_context",
        {
            "task": case["task"],
            "trusted_skill": {
                "skill_name": case["trusted_skill"].get("skill_name"),
                "mapped_tools": case["trusted_skill"].get("mapped_tools"),
            },
            "threat": {
                "threat_type": case["threat_profile"].get("threat_type"),
                "threat_subtype": case["threat_profile"].get("threat_subtype"),
                "description": case["threat_profile"].get("description"),
                "observation_refs": case["observation_refs"],
            },
            "prompt_messages": messages,
        },
    )

    _print_section("3. Start Local Scenario Runtime And Run Agent Framework")
    print(f"state_path: {DEFAULT_STATE_PATH}")
    print(f"apply_side_effects: {apply_side_effects}")
    print("agent_framework: ToolCallingAgentRunner")
    print("agent_client: ScriptedEmailAgentClient")

    client = ScriptedEmailAgentClient(_scripted_tool_calls_for_case(case_id))
    trajectory = run_live_agent_case(
        group,
        variant,
        client=client,  # type: ignore[arg-type]
        state_path=DEFAULT_STATE_PATH,
        max_turns=8,
        apply_side_effects=apply_side_effects,
    )

    _print_section("4. Tool Call Trace")
    for index, step in enumerate(trajectory["steps"], start=1):
        phase = step.get("phase")
        if phase == "assistant_message":
            print(f"{index:02d}. assistant_message tool_call_count={step.get('tool_call_count')}")
            if step.get("content"):
                print(f"    content: {step['content']}")
            continue
        if phase == "agent_tool_call":
            print(f"{index:02d}. tool={step.get('tool')} agent_tool={step.get('agent_tool_name')}")
            print(f"    arguments: {json.dumps(step.get('arguments'), sort_keys=True, ensure_ascii=False)}")
            result = step.get("result", {})
            print(f"    ok: {result.get('ok')} native_tool: {result.get('tool')}")

    _print_section("5. Candidate Invocation")
    candidate = trajectory.get("candidate_invocation")
    selection = trajectory.get("runner_metadata", {}).get("candidate_selection")
    _print_json_summary("candidate_invocation", candidate)
    _print_json_summary("candidate_selection", selection)

    _print_section("6. Persist Artifacts")
    write_trajectory_files([trajectory], output_dir / "trajectories")
    candidate_record = candidate_record_from_trajectory(dict(trajectory))
    candidate_record_path = output_dir / "candidate_records.jsonl"
    write_jsonl([candidate_record], candidate_record_path)
    print(f"trajectory_dir: {output_dir / 'trajectories'}")
    print(f"candidate_record: {candidate_record_path}")

    _print_section("Done")
    print("This demo used the same scenario API, tool-calling framework, and candidate extraction path as live runs.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Demonstrate the AuthSkillBench scenario-to-candidate flow.")
    parser.add_argument("--case", default=DEFAULT_CASE_ID, help="Case id to run in scripted demo mode.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--apply-side-effects",
        action="store_true",
        help="Apply mutating email actions to in-memory scenario state. Defaults to dry-run previews.",
    )
    args = parser.parse_args()
    return run_demo(args.case, _resolve(args.output_dir), apply_side_effects=args.apply_side_effects)


if __name__ == "__main__":
    raise SystemExit(main())
