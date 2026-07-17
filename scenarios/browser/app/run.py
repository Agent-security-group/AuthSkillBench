# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from .benchmark import BenchmarkGenerator


def main():
    scenario_dir = Path(__file__).resolve().parent.parent
    generator = BenchmarkGenerator(scenario_dir)

    print(f"Loading scenario from: {scenario_dir}")

    samples = generator.generate_all_samples()
    print(f"Generated {len(samples)} benchmark samples")

    for sample in samples:
        print(f"  - {sample.case_id}: {sample.task_type.name} x {sample.env_type.name}")

    generator.save_samples(samples)
    print(f"Saved samples to: {generator.output_dir / 'benchmark_samples.json'}")

    print("\nSample structure verification:")
    for sample in samples[:2]:
        print(f"\nCase: {sample.case_id}")
        print(f"  Task Type: {sample.task_type.name}")
        print(f"  Env Type: {sample.env_type.name}")
        print(f"  Decision: {sample.oracle_decision.name}")
        print(f"  Risk Tags: {[r.name for r in sample.risk_tags]}")


if __name__ == "__main__":
    main()
