#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from ..app.api import DEFAULT_STATE_PATH
    from ..app.benchmark import DEFAULT_CONTRAST_GROUPS_DIR
    from ..app.trajectory import DEFAULT_TRAJECTORIES_DIR, generate_trajectories, write_trajectory_files
except ImportError:  # pragma: no cover - supports direct script execution.
    sys.path.append(str(Path(__file__).resolve().parents[3]))
    from sandboxes.email.app.api import DEFAULT_STATE_PATH
    from sandboxes.email.app.benchmark import DEFAULT_CONTRAST_GROUPS_DIR
    from sandboxes.email.app.trajectory import DEFAULT_TRAJECTORIES_DIR, generate_trajectories, write_trajectory_files


ROOT = Path(__file__).resolve().parents[3]


def _resolve(path: Path | None) -> Path | None:
    if path is None or path.is_absolute():
        return path
    return ROOT / path


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate fixture-replay agent trajectories for the email sandbox.")
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE_PATH)
    parser.add_argument("--contrast-groups-dir", type=Path, default=DEFAULT_CONTRAST_GROUPS_DIR)
    parser.add_argument("--case", action="append", default=[], help="Case id or contrast-group id to run. Can be repeated.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_TRAJECTORIES_DIR)
    parser.add_argument("--stdout", action="store_true", help="Print trajectories to stdout instead of writing files.")
    args = parser.parse_args()

    trajectories = generate_trajectories(
        selected=args.case,
        state_path=_resolve(args.state) or DEFAULT_STATE_PATH,
        contrast_groups_dir=_resolve(args.contrast_groups_dir) or DEFAULT_CONTRAST_GROUPS_DIR,
    )

    if args.stdout:
        for trajectory in trajectories:
            print(json.dumps(trajectory, indent=2, sort_keys=False))
        return 0

    output_dir = _resolve(args.output_dir) or DEFAULT_TRAJECTORIES_DIR
    write_trajectory_files(trajectories, output_dir)
    print(f"Wrote {len(trajectories)} email sandbox trajectory file(s) to {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
