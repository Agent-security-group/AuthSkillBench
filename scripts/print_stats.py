#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path

from common import read_jsonl


def count_field(rows: list[dict], getter) -> Counter:
    counts: Counter = Counter()
    for row in rows:
        counts[getter(row)] += 1
    return counts


def print_counter(title: str, counter: Counter) -> None:
    print(title)
    for key, value in sorted(counter.items(), key=lambda item: str(item[0])):
        print(f"  {key}: {value}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Print AuthSkillBench dataset statistics.")
    parser.add_argument("dataset", type=Path)
    args = parser.parse_args()

    rows = read_jsonl(args.dataset)
    print(f"samples: {len(rows)}")

    print_counter("decisions:", count_field(rows, lambda r: r["expected_decision"]))
    print_counter("scenarios:", count_field(rows, lambda r: r["scenario"]))
    print_counter("task_types:", count_field(rows, lambda r: r["task"]["task_type"]))
    print_counter("task_families:", count_field(rows, lambda r: r["task"].get("task_family", "<none>")))
    print_counter("environment_types:", count_field(rows, lambda r: r["environment"]["environment_type"]))
    print_counter("environment_subtypes:", count_field(rows, lambda r: r["environment"].get("environment_subtype", "<none>")))
    print_counter("risk_types:", count_field(rows, lambda r: r["hidden_metadata"]["risk_type"]))

    groups: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        groups[row["contrast_group_id"]].add(row["expected_decision"])

    print("contrast_groups:")
    for group_id in sorted(groups):
        labels = ", ".join(sorted(groups[group_id]))
        print(f"  {group_id}: {labels}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
