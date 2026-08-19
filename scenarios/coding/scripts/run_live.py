#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
sys.dont_write_bytecode = True
from pathlib import Path

try:
    from ..app.agent_runner import run_live_agent_cases, write_live_trajectories
    from ..app.api import DEFAULT_STATE_PATH
    from ..app.benchmark import DEFAULT_CONTRAST_GROUPS_DIR, write_jsonl
    from ..app.trajectory import DEFAULT_TRAJECTORIES_DIR
    from ..app.trajectory_samples import candidate_record_from_trajectory
except ImportError:  # pragma: no cover - supports direct script execution.
    sys.path.append(str(Path(__file__).resolve().parents[3]))
    from scenarios.coding.app.agent_runner import run_live_agent_cases, write_live_trajectories
    from scenarios.coding.app.api import DEFAULT_STATE_PATH
    from scenarios.coding.app.benchmark import DEFAULT_CONTRAST_GROUPS_DIR, write_jsonl
    from scenarios.coding.app.trajectory import DEFAULT_TRAJECTORIES_DIR
    from scenarios.coding.app.trajectory_samples import candidate_record_from_trajectory


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ENV_FILE = ROOT / ".env"


def _resolve(path: Path | None) -> Path | None:
    if path is None or path.is_absolute():
        return path
    return ROOT / path


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line_no, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        if "=" not in line:
            raise SystemExit(f"Invalid env line in {path}:{line_no}: {raw_line}")
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if not key:
            raise SystemExit(f"Invalid env key in {path}:{line_no}: {raw_line}")
        os.environ.setdefault(key, value)


def _write_candidate_records(
    trajectories: list[dict],
    output: Path,
    skip_report: Path | None = None,
    fail_on_missing_candidate: bool = False,
) -> None:
    records: list[dict] = []
    skipped: list[dict] = []
    for trajectory in trajectories:
        try:
            records.append(candidate_record_from_trajectory(dict(trajectory)))
        except ValueError:
            skipped.append(
                {
                    "trajectory_id": trajectory.get("trajectory_id"),
                    "case_id": trajectory.get("case_id"),
                    "reason": "missing_candidate_invocation",
                }
            )
            if fail_on_missing_candidate:
                raise SystemExit(
                    f"{trajectory.get('trajectory_id', '<unknown>')}: missing candidate_invocation"
                )

    write_jsonl(records, output)
    print(f"Wrote {len(records)} candidate record(s) from {len(trajectories)} live trajectory file(s) to {output}")
    if skipped and skip_report:
        skip_report.parent.mkdir(parents=True, exist_ok=True)
        with skip_report.open("w", encoding="utf-8") as f:
            json.dump(skipped, f, indent=2, sort_keys=False)
            f.write("\n")
        print(f"Skipped {len(skipped)} live trajectory file(s); report written to {skip_report}", file=sys.stderr)
    elif skipped:
        print(f"Skipped {len(skipped)} live trajectory file(s) without candidate_invocation", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a real LLM agent against the coding scenario.")
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE_PATH)
    parser.add_argument("--contrast-groups-dir", type=Path, default=DEFAULT_CONTRAST_GROUPS_DIR)
    parser.add_argument("--case", action="append", default=[], help="Case id or contrast-group id to run. Can be repeated.")
    parser.add_argument("--model", help="DeepSeek model name. Defaults to DEEPSEEK_MODEL or deepseek-v4-flash.")
    parser.add_argument("--base-url", help="DeepSeek-compatible API base URL. Defaults to DEEPSEEK_BASE_URL or https://api.deepseek.com.")
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE, help="Env file with DEEPSEEK_API_KEY/DEEPSEEK_MODEL/DEEPSEEK_BASE_URL exports.")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-turns", type=int, default=25)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_TRAJECTORIES_DIR)
    parser.add_argument(
        "--candidate-records-output",
        type=Path,
        help="Write candidate-record JSONL directly from the DeepSeek live trajectories.",
    )
    parser.add_argument("--skip-report", type=Path, help="Write skipped live trajectory report to this JSON file.")
    parser.add_argument(
        "--fail-on-missing-candidate",
        action="store_true",
        help="Fail if a live trajectory has no candidate invocation instead of skipping it.",
    )
    parser.add_argument("--stdout", action="store_true", help="Print trajectories to stdout instead of writing files.")
    args = parser.parse_args()
    env_file = _resolve(args.env_file) or DEFAULT_ENV_FILE
    _load_env_file(env_file)

    try:
        trajectories = run_live_agent_cases(
            selected=args.case,
            state_path=_resolve(args.state) or DEFAULT_STATE_PATH,
            contrast_groups_dir=_resolve(args.contrast_groups_dir) or DEFAULT_CONTRAST_GROUPS_DIR,
            model=args.model,
            base_url=args.base_url,
            temperature=args.temperature,
            max_turns=args.max_turns,
        )
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc

    if args.stdout:
        for trajectory in trajectories:
            print(json.dumps(trajectory, indent=2, sort_keys=False))
        if args.candidate_records_output:
            _write_candidate_records(
                trajectories,
                _resolve(args.candidate_records_output) or args.candidate_records_output,
                skip_report=_resolve(args.skip_report) if args.skip_report else None,
                fail_on_missing_candidate=args.fail_on_missing_candidate,
            )
        return 0

    output_dir = _resolve(args.output_dir) or DEFAULT_TRAJECTORIES_DIR
    write_live_trajectories(trajectories, output_dir=output_dir)
    print(f"Wrote {len(trajectories)} live coding agent trajectory file(s) to {output_dir}")
    if args.candidate_records_output:
        _write_candidate_records(
            trajectories,
            _resolve(args.candidate_records_output) or args.candidate_records_output,
            skip_report=_resolve(args.skip_report) if args.skip_report else None,
            fail_on_missing_candidate=args.fail_on_missing_candidate,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
