#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from common import read_json, repo_root


ROOT = repo_root()


def load_ref(ref: str) -> dict[str, Any]:
    return read_json(ROOT / ref)


def require_same_sample(sample_id: str, *objects: dict[str, Any]) -> None:
    for obj in objects:
        if obj.get("sample_id") != sample_id:
            raise ValueError(f"sample_id mismatch for {sample_id}: got {obj.get('sample_id')}")


def row_from_sample_index(sample_index: dict[str, Any]) -> dict[str, Any]:
    sample_id = sample_index["sample_id"]
    task = load_ref(sample_index["task_ref"])
    environment = load_ref(sample_index["environment_ref"])
    candidate = load_ref(sample_index["candidate_invocation_ref"])
    authorization = load_ref(sample_index["authorization_ref"])
    metadata = load_ref(sample_index["metadata_ref"])

    require_same_sample(sample_id, task, environment, candidate, authorization, metadata)

    return {
        "sample_id": sample_id,
        "scenario": sample_index["scenario"],
        "contrast_group_id": sample_index["contrast_group_id"],
        "task": {
            "task_type": task["task_type"],
            "description": task["description"],
        },
        "environment": {
            "environment_type": environment["environment_type"],
            "source": environment["source"],
            "content": environment["content"],
        },
        "skill_set_ref": sample_index["skill_set_ref"],
        "candidate_invocation": candidate["candidate_invocation"],
        "expected_decision": authorization["expected_decision"],
        "gold_rationale": authorization["gold_rationale"],
        "fallback_invocation": authorization.get("fallback_invocation"),
        "hidden_metadata": metadata["hidden_metadata"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Rebuild seed JSONL from materialized case files.")
    parser.add_argument("cases_dir", type=Path, nargs="?", default=ROOT / "data" / "cases")
    parser.add_argument("output", type=Path, nargs="?", default=ROOT / "data" / "samples" / "authskillbench_v0_seed.jsonl")
    args = parser.parse_args()

    cases_dir = args.cases_dir if args.cases_dir.is_absolute() else ROOT / args.cases_dir
    output = args.output if args.output.is_absolute() else ROOT / args.output
    manifest = read_json(cases_dir / "manifest.json")

    sample_indexes = [load_ref(item["sample_ref"]) for item in manifest["samples"]]
    sample_indexes.sort(key=lambda item: item["order"])
    rows = [row_from_sample_index(sample_index) for sample_index in sample_indexes]

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, separators=(",", ":"), sort_keys=False) + "\n")

    try:
        output_label = str(output.relative_to(ROOT))
    except ValueError:
        output_label = str(output)
    print(f"Wrote {len(rows)} samples to {output_label}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
