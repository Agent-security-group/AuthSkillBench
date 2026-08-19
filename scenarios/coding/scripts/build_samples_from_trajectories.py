#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from ..app.benchmark import write_jsonl
    from ..app.trajectory_samples import candidate_records_from_trajectory_paths, iter_trajectory_paths
except ImportError:  # pragma: no cover - supports direct script execution.
    sys.path.append(str(Path(__file__).resolve().parents[3]))
    from scenarios.coding.app.benchmark import write_jsonl
    from scenarios.coding.app.trajectory_samples import candidate_records_from_trajectory_paths, iter_trajectory_paths


ROOT = Path(__file__).resolve().parents[3]


def _resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def main() -> int:
    parser = argparse.ArgumentParser(description="Build candidate records from coding scenario trajectory files.")
    parser.add_argument("trajectories", nargs="+", type=Path, help="Trajectory file(s) or directory/directories.")
    parser.add_argument("--output", type=Path, help="Write generated candidate-record JSONL to this path. Defaults to stdout.")
    parser.add_argument(
        "--include-missing-candidate",
        action="store_true",
        help="Fail instead of skipping trajectories that do not contain a candidate_invocation.",
    )
    parser.add_argument("--skip-report", type=Path, help="Write skipped trajectory report to this JSON file.")
    parser.add_argument("--indent", action="store_true", help="Pretty-print JSON when writing to stdout.")
    args = parser.parse_args()

    inputs = [_resolve(path) for path in args.trajectories]
    paths = iter_trajectory_paths(inputs)
    if not paths:
        raise SystemExit("No trajectory files found")

    try:
        records, skipped = candidate_records_from_trajectory_paths(
            paths,
            skip_without_candidate=not args.include_missing_candidate,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    output = args.output if not args.output or args.output.is_absolute() else ROOT / args.output
    if output:
        write_jsonl(records, output)
        print(f"Wrote {len(records)} candidate record(s) from {len(paths)} trajectory file(s) to {output}")
    else:
        for record in records:
            if args.indent:
                print(json.dumps(record, indent=2, sort_keys=False))
            else:
                print(json.dumps(record, sort_keys=True))

    if skipped:
        message = f"Skipped {len(skipped)} trajectory file(s) without candidate_invocation"
        if args.skip_report:
            skip_report = args.skip_report if args.skip_report.is_absolute() else ROOT / args.skip_report
            skip_report.parent.mkdir(parents=True, exist_ok=True)
            with skip_report.open("w", encoding="utf-8") as f:
                json.dump(skipped, f, indent=2, sort_keys=False)
                f.write("\n")
            message += f"; report written to {skip_report}"
        print(message, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
