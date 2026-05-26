#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from ..app.live_report import (
        DEFAULT_LIVE_CANDIDATE_RECORDS,
        DEFAULT_LIVE_SKIPPED,
        DEFAULT_LIVE_TRAJECTORIES_DIR,
        DEFAULT_REPORTS_DIR,
        build_live_run_report_from_paths,
        write_text,
    )
except ImportError:  # pragma: no cover - supports direct script execution.
    sys.path.append(str(Path(__file__).resolve().parents[3]))
    from scenarios.email.app.live_report import (
        DEFAULT_LIVE_CANDIDATE_RECORDS,
        DEFAULT_LIVE_SKIPPED,
        DEFAULT_LIVE_TRAJECTORIES_DIR,
        DEFAULT_REPORTS_DIR,
        build_live_run_report_from_paths,
        write_text,
    )


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT = DEFAULT_REPORTS_DIR / "live_run_summary.md"


def _resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a Markdown summary for an email live agent run.")
    parser.add_argument(
        "trajectories",
        nargs="*",
        type=Path,
        default=[DEFAULT_LIVE_TRAJECTORIES_DIR],
        help="Trajectory file(s) or directories. Defaults to scenarios/email/outputs/live_trajectories.",
    )
    parser.add_argument("--candidate-records", type=Path, default=DEFAULT_LIVE_CANDIDATE_RECORDS)
    parser.add_argument("--skipped", type=Path, default=DEFAULT_LIVE_SKIPPED)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--stdout", action="store_true", help="Print report instead of writing a file.")
    args = parser.parse_args()

    report = build_live_run_report_from_paths(
        [_resolve(path) for path in args.trajectories],
        candidate_records_path=_resolve(args.candidate_records),
        skipped_path=_resolve(args.skipped),
    )

    if args.stdout:
        print(report, end="")
        return 0

    output = _resolve(args.output)
    write_text(report, output)
    print(f"Wrote email live run report to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
