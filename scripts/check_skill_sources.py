#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def operation_exists(artifact: dict[str, Any], operation: str) -> bool:
    return (
        operation in artifact.get("selected_operations", {})
        or operation in artifact.get("selected_methods", {})
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Check that skill sets are backed by real source artifacts.")
    parser.add_argument("skill_dir", type=Path, nargs="?", default=ROOT / "data" / "skills")
    args = parser.parse_args()

    errors: list[str] = []
    artifact_cache: dict[Path, dict[str, Any]] = {}

    for path in sorted(args.skill_dir.glob("*.skills.json")):
        skill_set = read_json(path)
        for skill in skill_set.get("skills", []):
            name = skill.get("name", "<unnamed>")
            provenance = skill.get("source_provenance")
            if not isinstance(provenance, dict):
                errors.append(f"{path.name}:{name}: missing source_provenance")
                continue

            source_type = provenance.get("source_type")
            if source_type == "constructed_common_utility":
                errors.append(f"{path.name}:{name}: constructed utilities are not allowed")
                continue

            skill_file = skill.get("skill_file")
            if not skill_file:
                errors.append(f"{path.name}:{name}: missing skill_file")
            elif not (ROOT / skill_file).exists():
                errors.append(f"{path.name}:{name}: skill_file does not exist: {skill_file}")

            artifact_ref = provenance.get("source_artifact")
            operation = provenance.get("source_operation")
            if not artifact_ref or not operation:
                errors.append(f"{path.name}:{name}: missing source_artifact or source_operation")
                continue

            artifact_path = ROOT / artifact_ref
            if not artifact_path.exists():
                errors.append(f"{path.name}:{name}: source artifact does not exist: {artifact_ref}")
                continue

            if artifact_path not in artifact_cache:
                artifact_cache[artifact_path] = read_json(artifact_path)
            artifact = artifact_cache[artifact_path]
            if not operation_exists(artifact, operation):
                errors.append(f"{path.name}:{name}: operation {operation!r} not found in {artifact_ref}")

            real_schema = skill.get("real_tool_schema")
            projection = skill.get("benchmark_projection")
            if not isinstance(real_schema, dict):
                errors.append(f"{path.name}:{name}: missing real_tool_schema")
            if not isinstance(projection, dict) or "arguments_schema" not in projection:
                errors.append(f"{path.name}:{name}: missing benchmark_projection.arguments_schema")

    if errors:
        print(f"Skill source check failed with {len(errors)} error(s):")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"Skill source check passed: {args.skill_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
