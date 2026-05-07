#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from common import load_skill_set, read_jsonl


def default_id_map_path(output: Path) -> Path:
    return output.with_name(f"{output.stem}.id_map.json")


def public_input_id(prefix: str, sample_id: str) -> str:
    digest = hashlib.sha256(f"{prefix}:{sample_id}".encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{digest}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Materialize model inputs without gold labels or hidden metadata.")
    parser.add_argument("dataset", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--id-map",
        type=Path,
        help="Write the private input_id -> sample_id map used by scoring. Defaults to <output-stem>.id_map.json.",
    )
    parser.add_argument(
        "--public-id-prefix",
        default="asb_v0",
        help="Opaque public id prefix used in model inputs.",
    )
    parser.add_argument(
        "--include-sources",
        action="store_true",
        help="Include source URLs from skill set files in the model input.",
    )
    args = parser.parse_args()

    rows = read_jsonl(args.dataset)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    id_map_path = args.id_map or default_id_map_path(args.output)
    id_map_path.parent.mkdir(parents=True, exist_ok=True)
    skill_cache = {}
    id_map_records = []
    input_ids = set()

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

            input_id = public_input_id(args.public_id_prefix, row["sample_id"])
            if input_id in input_ids:
                raise ValueError(f"duplicate generated input_id: {input_id}")
            input_ids.add(input_id)
            id_map_records.append(
                {
                    "input_id": input_id,
                    "sample_id": row["sample_id"],
                }
            )
            model_input = {
                "input_id": input_id,
                "scenario": row["scenario"],
                "task": {
                    "description": row["task"]["description"],
                },
                "environment": {
                    "source": row["environment"]["source"],
                    "content": row["environment"]["content"],
                },
                "skill_set": skill_cache[skill_set_ref],
                "candidate_invocation": row["candidate_invocation"],
                "output_schema": {
                    "input_id": "copy this input_id",
                    "decision": "Allow|Deny|Ask|Defer|Fallback",
                    "rationale": "short explanation",
                    "fallback_invocation": "optional invocation object when decision is Fallback",
                },
            }
            f.write(json.dumps(model_input, sort_keys=True) + "\n")

    id_map = {
        "schema_version": "authskillbench.input_id_map.v1",
        "model_input_file": str(args.output),
        "gold_dataset_file": str(args.dataset),
        "records": id_map_records,
    }
    with id_map_path.open("w", encoding="utf-8") as f:
        json.dump(id_map, f, indent=2, sort_keys=False)
        f.write("\n")

    print(f"Wrote model inputs: {args.output}")
    print(f"Wrote input id map: {id_map_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
