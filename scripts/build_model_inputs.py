#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import load_skill_set, read_jsonl


def main() -> int:
    parser = argparse.ArgumentParser(description="Materialize model inputs without gold labels or hidden metadata.")
    parser.add_argument("dataset", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--include-sources",
        action="store_true",
        help="Include source URLs from skill set files in the model input.",
    )
    args = parser.parse_args()

    rows = read_jsonl(args.dataset)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    skill_cache = {}

    with args.output.open("w", encoding="utf-8") as f:
        for row in rows:
            skill_set_ref = row["skill_set_ref"]
            if skill_set_ref not in skill_cache:
                skill_set = load_skill_set(skill_set_ref)
                public_skill_set = {
                    "scenario": skill_set["scenario"],
                    "description": skill_set["description"],
                    "skills": skill_set["skills"],
                }
                if args.include_sources:
                    public_skill_set["sources"] = skill_set.get("sources", [])
                skill_cache[skill_set_ref] = public_skill_set

            model_input = {
                "sample_id": row["sample_id"],
                "scenario": row["scenario"],
                "task": row["task"],
                "environment": row["environment"],
                "skill_set": skill_cache[skill_set_ref],
                "candidate_invocation": row["candidate_invocation"],
                "output_schema": {
                    "decision": "Allow|Deny|Ask|Defer|Fallback",
                    "rationale": "short explanation",
                    "fallback_invocation": "optional invocation object when decision is Fallback",
                },
            }
            f.write(json.dumps(model_input, sort_keys=True) + "\n")

    print(f"Wrote model inputs: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

