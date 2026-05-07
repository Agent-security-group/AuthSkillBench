#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "data" / "skills"
REGISTRY_DIR = SKILL_DIR / "registry"


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=False)
        f.write("\n")


def safe_skill_filename(skill_name: str) -> str:
    return skill_name.replace(".", "__").replace("/", "__") + ".skill.json"


def main() -> int:
    if REGISTRY_DIR.exists():
        shutil.rmtree(REGISTRY_DIR)
    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)

    manifest: dict[str, Any] = {
        "description": "Local per-skill registry. Each file is materialized from source-derived real_tool_schema plus benchmark projection.",
        "skills": {},
    }

    for scenario_path in sorted(SKILL_DIR.glob("*.skills.json")):
        skill_set = read_json(scenario_path)
        scenario = skill_set["scenario"]
        scenario_registry = REGISTRY_DIR / scenario

        for skill in skill_set.get("skills", []):
            source_type = skill.get("source_provenance", {}).get("source_type")
            if source_type == "constructed_common_utility":
                raise ValueError(f"constructed skill is not allowed: {skill['name']}")

            rel_path = Path("data") / "skills" / "registry" / scenario / safe_skill_filename(skill["name"])
            skill["skill_file"] = str(rel_path)
            materialized = {
                "schema_version": "authskillbench.skill.v1",
                "scenario": scenario,
                **skill,
            }
            write_json(ROOT / rel_path, materialized)
            manifest["skills"][skill["name"]] = {
                "scenario": scenario,
                "skill_file": str(rel_path),
                "source_provenance": skill.get("source_provenance"),
            }

        write_json(scenario_path, skill_set)
        print(f"updated {scenario_path.relative_to(ROOT)}")

    write_json(REGISTRY_DIR / "manifest.json", manifest)
    print(f"wrote {(REGISTRY_DIR / 'manifest.json').relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

