#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

from common import read_jsonl, repo_root


ROOT = repo_root()


def write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=False)
        f.write("\n")


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def case_paths(cases_dir: Path, row: dict[str, Any]) -> dict[str, Path]:
    sample_id = row["sample_id"]
    scenario = row["scenario"]
    contrast_group = row["contrast_group_id"]
    task_type = row["task"]["task_type"]
    environment_type = row["environment"]["environment_type"]
    decision = row["expected_decision"]

    return {
        "task": cases_dir / "tasks" / scenario / task_type / f"{sample_id}.task.json",
        "environment": cases_dir / "environments" / scenario / environment_type / f"{sample_id}.environment.json",
        "candidate_invocation": cases_dir / "candidate_invocations" / scenario / contrast_group / f"{sample_id}.candidate_invocation.json",
        "authorization": cases_dir / "authorizations" / scenario / decision / f"{sample_id}.authorization.json",
        "metadata": cases_dir / "metadata" / scenario / f"{sample_id}.metadata.json",
        "sample": cases_dir / "samples" / scenario / contrast_group / f"{sample_id}.sample.json",
    }


def materialize_row(cases_dir: Path, row: dict[str, Any], order: int) -> dict[str, Any]:
    paths = case_paths(cases_dir, row)
    sample_id = row["sample_id"]
    scenario = row["scenario"]
    contrast_group = row["contrast_group_id"]

    task_obj = {
        "sample_id": sample_id,
        "scenario": scenario,
        "contrast_group_id": contrast_group,
        **row["task"],
    }
    environment_obj = {
        "sample_id": sample_id,
        "scenario": scenario,
        "contrast_group_id": contrast_group,
        **row["environment"],
    }
    candidate_obj = {
        "sample_id": sample_id,
        "scenario": scenario,
        "contrast_group_id": contrast_group,
        "skill_set_ref": row["skill_set_ref"],
        "candidate_invocation": row["candidate_invocation"],
    }
    authorization_obj = {
        "sample_id": sample_id,
        "scenario": scenario,
        "contrast_group_id": contrast_group,
        "expected_decision": row["expected_decision"],
        "gold_rationale": row["gold_rationale"],
        "fallback_invocation": row.get("fallback_invocation"),
    }
    metadata_obj = {
        "sample_id": sample_id,
        "scenario": scenario,
        "contrast_group_id": contrast_group,
        "hidden_metadata": row["hidden_metadata"],
    }

    refs = {
        "task_ref": rel(paths["task"]),
        "environment_ref": rel(paths["environment"]),
        "candidate_invocation_ref": rel(paths["candidate_invocation"]),
        "authorization_ref": rel(paths["authorization"]),
        "metadata_ref": rel(paths["metadata"]),
    }
    sample_obj = {
        "sample_id": sample_id,
        "order": order,
        "scenario": scenario,
        "contrast_group_id": contrast_group,
        "skill_set_ref": row["skill_set_ref"],
        **refs,
    }

    write_json(paths["task"], task_obj)
    write_json(paths["environment"], environment_obj)
    write_json(paths["candidate_invocation"], candidate_obj)
    write_json(paths["authorization"], authorization_obj)
    write_json(paths["metadata"], metadata_obj)
    write_json(paths["sample"], sample_obj)

    return {
        "sample_id": sample_id,
        "order": order,
        "scenario": scenario,
        "contrast_group_id": contrast_group,
        "sample_ref": rel(paths["sample"]),
        **refs,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Materialize AuthSkillBench JSONL samples into per-component case files.")
    parser.add_argument("dataset", type=Path, default=ROOT / "data" / "samples" / "authskillbench_v0_seed.jsonl")
    parser.add_argument("cases_dir", type=Path, nargs="?", default=ROOT / "data" / "cases")
    args = parser.parse_args()

    dataset = args.dataset if args.dataset.is_absolute() else ROOT / args.dataset
    cases_dir = args.cases_dir if args.cases_dir.is_absolute() else ROOT / args.cases_dir

    rows = read_jsonl(dataset)
    if cases_dir.exists():
        shutil.rmtree(cases_dir)
    cases_dir.mkdir(parents=True, exist_ok=True)

    manifest_rows = []
    for order, row in enumerate(rows, start=1):
        row = {key: value for key, value in row.items() if not key.startswith("_")}
        manifest_rows.append(materialize_row(cases_dir, row, order))

    manifest = {
        "schema_version": "authskillbench.case_files.v1",
        "source_dataset": rel(dataset),
        "description": "Human-manageable component view of AuthSkillBench samples.",
        "layout": {
            "tasks": "data/cases/tasks/<scenario>/<task_type>/<sample_id>.task.json",
            "environments": "data/cases/environments/<scenario>/<environment_type>/<sample_id>.environment.json",
            "candidate_invocations": "data/cases/candidate_invocations/<scenario>/<contrast_group_id>/<sample_id>.candidate_invocation.json",
            "authorizations": "data/cases/authorizations/<scenario>/<expected_decision>/<sample_id>.authorization.json",
            "metadata": "data/cases/metadata/<scenario>/<sample_id>.metadata.json",
            "samples": "data/cases/samples/<scenario>/<contrast_group_id>/<sample_id>.sample.json",
        },
        "samples": manifest_rows,
    }
    write_json(cases_dir / "manifest.json", manifest)
    print(f"Wrote {len(rows)} case file groups to {rel(cases_dir)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

