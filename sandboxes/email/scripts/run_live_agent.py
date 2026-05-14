#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

try:
    from ..app.agent_runner import run_live_agent_cases, write_live_trajectories
    from ..app.api import DEFAULT_STATE_PATH
    from ..app.benchmark import DEFAULT_CONTRAST_GROUPS_DIR
    from ..app.trajectory import DEFAULT_TRAJECTORIES_DIR
except ImportError:  # pragma: no cover - supports direct script execution.
    sys.path.append(str(Path(__file__).resolve().parents[3]))
    from sandboxes.email.app.agent_runner import run_live_agent_cases, write_live_trajectories
    from sandboxes.email.app.api import DEFAULT_STATE_PATH
    from sandboxes.email.app.benchmark import DEFAULT_CONTRAST_GROUPS_DIR
    from sandboxes.email.app.trajectory import DEFAULT_TRAJECTORIES_DIR


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
            line = line[len("export ") :].strip()
        if "=" not in line:
            raise SystemExit(f"Invalid env line in {path}:{line_no}: {raw_line}")
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if not key:
            raise SystemExit(f"Invalid env key in {path}:{line_no}: {raw_line}")
        os.environ.setdefault(key, value)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a real LLM agent against the email sandbox.")
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE_PATH)
    parser.add_argument("--contrast-groups-dir", type=Path, default=DEFAULT_CONTRAST_GROUPS_DIR)
    parser.add_argument("--case", action="append", default=[], help="Case id or contrast-group id to run. Can be repeated.")
    parser.add_argument("--model", help="DeepSeek model name. Defaults to DEEPSEEK_MODEL or deepseek-v4-flash.")
    parser.add_argument("--base-url", help="DeepSeek-compatible API base URL. Defaults to DEEPSEEK_BASE_URL or https://api.deepseek.com.")
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE, help="Env file with DEEPSEEK_API_KEY/DEEPSEEK_MODEL/DEEPSEEK_BASE_URL exports.")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-turns", type=int, default=8)
    parser.add_argument("--apply-side-effects", action="store_true", help="Allow mutating sandbox sends/drafts during the run.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_TRAJECTORIES_DIR)
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
            apply_side_effects=args.apply_side_effects,
        )
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc

    if args.stdout:
        for trajectory in trajectories:
            print(json.dumps(trajectory, indent=2, sort_keys=False))
        return 0

    output_dir = _resolve(args.output_dir) or DEFAULT_TRAJECTORIES_DIR
    write_live_trajectories(trajectories, output_dir=output_dir)
    print(f"Wrote {len(trajectories)} live email agent trajectory file(s) to {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
