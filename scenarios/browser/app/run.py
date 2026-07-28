# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .benchmark import (
    DEFAULT_CONTRAST_GROUPS_DIR,
    DEFAULT_OUTPUT_DIR,
    compose_case_from_variant,
    iter_case_specs,
    write_jsonl,
)


def main():
    scenario_dir = Path(__file__).resolve().parent.parent
    output_dir = scenario_dir / "outputs"

    print(f"Loading scenario from: {scenario_dir}")
    print(f"Contrast groups dir: {DEFAULT_CONTRAST_GROUPS_DIR}")

    specs = iter_case_specs()
    print(f"Found {len(specs)} case specifications")

    samples: list[dict[str, Any]] = []
    for group, variant in specs:
        try:
            case = compose_case_from_variant(group, variant)
            samples.append(case)
        except Exception as e:
            case_id = variant.get("case_id", "<unknown>")
            print(f"  WARNING: Failed to compose {case_id}: {e}")

    print(f"\nGenerated {len(samples)} benchmark samples")

    task_families: dict[str, int] = {}
    task_types: dict[str, int] = {}
    for s in samples:
        tf = s.get("task", {}).get("task_family", "unknown")
        tt = s.get("task", {}).get("task_type", "unknown")
        task_families[tf] = task_families.get(tf, 0) + 1
        task_types[tt] = task_types.get(tt, 0) + 1

    print("\nBy task family:")
    for fam, count in sorted(task_families.items()):
        print(f"  {fam}: {count}")

    print("\nBy task type:")
    for tt, count in sorted(task_types.items()):
        print(f"  {tt}: {count}")

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "benchmark_samples.json"
    write_jsonl(samples, output_path)
    print(f"\nSaved {len(samples)} samples to: {output_path}")

    print("\nSample structure verification (first 2 cases):")
    for sample in samples[:2]:
        print(f"\n  Case: {sample['case_id']}")
        print(f"    Task: {sample.get('task', {}).get('description', 'N/A')[:80]}...")
        print(f"    Threat: {sample.get('threat_type', 'N/A')}")
        print(f"    Skill: {sample.get('skill_under_test', 'N/A')}")


if __name__ == "__main__":
    main()
