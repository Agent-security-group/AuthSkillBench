#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from ..app.api import DEFAULT_STATE_PATH
    from ..app.benchmark import DEFAULT_CONTRAST_GROUPS_DIR, DEFAULT_ENVIRONMENTS_DIR, generate_samples, write_jsonl
except ImportError:  # pragma: no cover - supports direct script execution.
    sys.path.append(str(Path(__file__).resolve().parents[3]))
    from sandboxes.email.app.api import DEFAULT_STATE_PATH
    from sandboxes.email.app.benchmark import (
        DEFAULT_CONTRAST_GROUPS_DIR,
        DEFAULT_ENVIRONMENTS_DIR,
        generate_samples,
        write_jsonl,
    )


ROOT = Path(__file__).resolve().parents[3]


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate AuthSkillBench-compatible samples from the email sandbox.")
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE_PATH)
    parser.add_argument("--contrast-groups-dir", type=Path, default=DEFAULT_CONTRAST_GROUPS_DIR)
    parser.add_argument("--environments-dir", type=Path, default=DEFAULT_ENVIRONMENTS_DIR)
    parser.add_argument("--case", action="append", default=[], help="Case id or contrast-group id to run. Can be repeated.")
    parser.add_argument("--output", type=Path, help="Write generated sample JSONL to this path. Defaults to stdout.")
    parser.add_argument("--indent", action="store_true", help="Pretty-print JSON when writing to stdout.")
    args = parser.parse_args()

    state_path = args.state if args.state.is_absolute() else ROOT / args.state
    contrast_groups_dir = (
        args.contrast_groups_dir if args.contrast_groups_dir.is_absolute() else ROOT / args.contrast_groups_dir
    )
    environments_dir = args.environments_dir if args.environments_dir.is_absolute() else ROOT / args.environments_dir
    output = args.output if not args.output or args.output.is_absolute() else ROOT / args.output

    try:
        samples = generate_samples(
            selected=args.case,
            state_path=state_path,
            contrast_groups_dir=contrast_groups_dir,
            environments_dir=environments_dir,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    if output:
        write_jsonl(samples, output)
        print(f"Wrote {len(samples)} email sandbox sample(s) to {output}")
    else:
        for sample in samples:
            if args.indent:
                print(json.dumps(sample, indent=2, sort_keys=False))
            else:
                print(json.dumps(sample, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
