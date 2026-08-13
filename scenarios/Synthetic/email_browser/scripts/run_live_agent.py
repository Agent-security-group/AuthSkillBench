from __future__ import annotations

import argparse
from pathlib import Path

from scenarios.Synthetic.email_browser.app.agent_runner import run_live_agent_cases, write_live_trajectories
from scenarios.Synthetic.email_browser.app.benchmark import DEFAULT_CONTRAST_GROUPS_DIR


def main() -> int:
    parser = argparse.ArgumentParser(description="Run live-agent synthetic Email + Browser cases.")
    parser.add_argument("--case", action="append", dest="cases", help="Case id, contrast group id, or group filename stem.")
    parser.add_argument("--contrast-groups-dir", type=Path, default=DEFAULT_CONTRAST_GROUPS_DIR)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parents[1] / "outputs" / "trajectories")
    parser.add_argument("--model")
    parser.add_argument("--base-url")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-turns", type=int, default=8)
    parser.add_argument("--apply-side-effects", action="store_true")
    args = parser.parse_args()

    trajectories = run_live_agent_cases(
        selected=args.cases,
        contrast_groups_dir=args.contrast_groups_dir,
        model=args.model,
        base_url=args.base_url,
        temperature=args.temperature,
        max_turns=args.max_turns,
        apply_side_effects=args.apply_side_effects,
    )
    write_live_trajectories(trajectories, output_dir=args.output_dir)
    print(f"wrote {len(trajectories)} trajectories to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

