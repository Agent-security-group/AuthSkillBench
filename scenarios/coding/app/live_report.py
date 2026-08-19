from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .trajectory_samples import iter_trajectory_paths, read_trajectory


DEFAULT_REPORTS_DIR = Path(__file__).resolve().parents[1] / "outputs" / "reports"
DEFAULT_LIVE_TRAJECTORIES_DIR = Path(__file__).resolve().parents[1] / "outputs" / "trajectories"
DEFAULT_LIVE_CANDIDATE_RECORDS = (
    Path(__file__).resolve().parents[1] / "outputs" / "candidate_records" / "live_candidate_records.jsonl"
)
DEFAULT_LIVE_SKIPPED = Path(__file__).resolve().parents[1] / "outputs" / "candidate_records" / "live_skipped.json"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"{path}:{line_no}: expected JSON object")
        rows.append(row)
    return rows


def read_skipped(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{path}: expected JSON array")
    return [item for item in data if isinstance(item, dict)]


def _one_line(value: Any, max_len: int = 180) -> str:
    if value is None:
        return ""
    text = str(value).replace("\n", " ").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rstrip() + "..."


def _json_inline(value: Any, max_len: int = 220) -> str:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rstrip() + "..."


def _tool_calls(trajectory: dict[str, Any]) -> list[dict[str, Any]]:
    steps = trajectory.get("steps")
    if not isinstance(steps, list):
        return []
    return [
        step
        for step in steps
        if isinstance(step, dict) and step.get("phase") == "agent_tool_call" and isinstance(step.get("tool"), str)
    ]


def _assistant_turn_count(trajectory: dict[str, Any]) -> int:
    steps = trajectory.get("steps")
    if not isinstance(steps, list):
        return 0
    return len([step for step in steps if isinstance(step, dict) and step.get("phase") == "assistant_message"])


def _candidate_records_by_case(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_case: dict[str, dict[str, Any]] = {}
    for record in records:
        case_id = record.get("case_id")
        if isinstance(case_id, str):
            by_case[case_id] = record
    return by_case


def _skipped_by_trajectory(skipped: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for item in skipped:
        trajectory_id = item.get("trajectory_id")
        if isinstance(trajectory_id, str):
            by_id[trajectory_id] = item
    return by_id


def _candidate_section(record: dict[str, Any] | None, skipped: dict[str, Any] | None) -> list[str]:
    if record is None:
        reason = skipped.get("reason") if skipped else "missing_candidate_invocation"
        return [f"- Candidate: none (`{reason}`)"]

    candidate = record.get("candidate_invocation") if isinstance(record, dict) else None
    if not isinstance(candidate, dict):
        return ["- Candidate: none (`missing_candidate_invocation`)"]

    lines = [f"- Candidate: `{candidate.get('skill')}`"]
    arguments = candidate.get("arguments")
    if isinstance(arguments, dict):
        lines.append(f"- Candidate arguments: `{_json_inline(arguments)}`")
    claimed_reason = candidate.get("claimed_reason")
    if claimed_reason:
        lines.append(f"- Candidate source: {_one_line(claimed_reason)}")

    metadata = record.get("runtime_metadata")
    selection = metadata.get("candidate_selection") if isinstance(metadata, dict) else None
    if isinstance(selection, dict):
        reasons = selection.get("selected_reasons") or []
        if reasons:
            lines.append(f"- Selection reasons: {', '.join(f'`{item}`' for item in reasons)}")
        step_index = selection.get("selected_step_index")
        if step_index is not None:
            lines.append(f"- Selected step index: `{step_index}`")
    return lines


def build_live_run_report(
    trajectories: list[dict[str, Any]],
    candidate_records: list[dict[str, Any]],
    skipped: list[dict[str, Any]],
) -> str:
    records_by_case = _candidate_records_by_case(candidate_records)
    skipped_by_id = _skipped_by_trajectory(skipped)
    case_count = len(trajectories)
    candidate_count = len(candidate_records)
    skipped_count = len(skipped)

    lines = [
        "# Coding Live Run Summary",
        "",
        f"- Trajectories: `{case_count}`",
        f"- Candidate records: `{candidate_count}`",
        f"- Skipped trajectories: `{skipped_count}`",
        "",
        "## Cases",
        "",
    ]

    for trajectory in sorted(trajectories, key=lambda item: str(item.get("case_id", ""))):
        case_id = str(trajectory.get("case_id"))
        trajectory_id = str(trajectory.get("trajectory_id"))
        record = records_by_case.get(case_id)
        skipped_item = skipped_by_id.get(trajectory_id)
        task = trajectory.get("task") if isinstance(trajectory.get("task"), dict) else {}
        threat = trajectory.get("threat_profile") if isinstance(trajectory.get("threat_profile"), dict) else {}
        tool_calls = _tool_calls(trajectory)

        lines.extend(
            [
                f"### `{case_id}`",
                "",
                f"- Source: `{trajectory.get('source')}` / `{trajectory.get('model')}`",
                f"- Contrast group: `{trajectory.get('contrast_group_id')}`",
                f"- Skill under test: `{trajectory.get('skill_under_test')}`",
                f"- Task: {_one_line(task.get('description'))}",
                f"- Task operation: `{task.get('operation')}`",
                f"- Threat: `{threat.get('threat_type')}` / `{threat.get('threat_subtype')}`",
                f"- Threat description: {_one_line(threat.get('description'))}",
                f"- Assistant turns: `{_assistant_turn_count(trajectory)}`",
                f"- Tool calls: `{len(tool_calls)}`",
            ]
        )

        for index, step in enumerate(tool_calls, start=1):
            lines.append(f"  - `{index}. {step.get('tool')}` `{_json_inline(step.get('arguments', {}), 160)}`")

        lines.extend(_candidate_section(record, skipped_item))
        final_message = trajectory.get("final_message")
        if isinstance(final_message, dict) and final_message.get("content"):
            lines.append(f"- Final message: {_one_line(final_message.get('content'), 260)}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def build_live_run_report_from_paths(
    trajectory_inputs: list[Path],
    candidate_records_path: Path = DEFAULT_LIVE_CANDIDATE_RECORDS,
    skipped_path: Path = DEFAULT_LIVE_SKIPPED,
) -> str:
    trajectory_paths = iter_trajectory_paths(trajectory_inputs)
    trajectories = [read_trajectory(path) for path in trajectory_paths]
    candidate_records = read_jsonl(candidate_records_path)
    skipped = read_skipped(skipped_path)
    return build_live_run_report(trajectories, candidate_records, skipped)


def write_text(text: str, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")
