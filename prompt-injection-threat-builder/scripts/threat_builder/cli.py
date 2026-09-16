from __future__ import annotations

import argparse
import json
from pathlib import Path

from .builder import UniversalThreatBuilder
from .evaluation import retain_successful_example
from .goals import list_goals


DEFAULT_OUTPUT_ROOT = Path(__file__).resolve().parents[3] / "runs" / "threat-builder" / "generated_threats"
DEFAULT_CATALOG = Path(__file__).resolve().parents[2] / "references" / "injection-seed-catalog.md"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate an offline AuthSkillBench threat profile")
    parser.add_argument("--scenario", choices=["email", "browser", "coding", "github", "workspace"])
    parser.add_argument("--task", help="task variant id")
    parser.add_argument("--operator", default="scope_expansion")
    parser.add_argument("--goal", help="goal id from the CIA x scenario catalog; overrides --operator")
    parser.add_argument("--seed", default="contextual:1", help="catalog seed id, optionally category-qualified (contextual:1 or obvious:1)")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--candidate", type=Path, help="candidate or trajectory JSON; retain only if the oracle matches")
    parser.add_argument("--success-root", type=Path, default=DEFAULT_OUTPUT_ROOT, help="root for successful examples")
    parser.add_argument("--list-goals", action="store_true", help="list the CIA x scenario goal catalog and exit")
    parser.add_argument("--category", choices=["confidentiality", "integrity", "availability"], help="CIA category for matrix generation")
    parser.add_argument("--all-goals", action="store_true", help="generate all goals in --category for the selected scenario")
    args = parser.parse_args()
    if args.list_goals:
        print(json.dumps([goal.to_dict() for goal in list_goals()], indent=2, ensure_ascii=False))
        return 0
    if not args.scenario or not args.task:
        parser.error("--scenario and --task are required unless --list-goals is used")
    if args.all_goals and not args.category:
        parser.error("--category is required with --all-goals")
    if args.all_goals:
        profiles = UniversalThreatBuilder(catalog_path=args.catalog).build_goal_matrix(args.category, args.scenario, args.task, args.seed)
        output_dir = args.output or DEFAULT_OUTPUT_ROOT
        output_dir.mkdir(parents=True, exist_ok=True)
        paths = []
        for item in profiles:
            path = output_dir / f"{item['threat_profile_id']}.json"
            path.write_text(json.dumps(item, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            paths.append(str(path))
        print(json.dumps({"generated": len(paths), "paths": paths}, ensure_ascii=False))
        return 0
    profile = UniversalThreatBuilder(catalog_path=args.catalog).build(args.scenario, args.task, args.operator, args.seed, goal_id=args.goal)
    text = json.dumps(profile, indent=2, ensure_ascii=False, sort_keys=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    if args.candidate:
        candidate = json.loads(args.candidate.read_text(encoding="utf-8"))
        retained, path, evaluation = retain_successful_example(profile, candidate, args.success_root)
        print(json.dumps({"retained": retained, "path": str(path) if path else None, "evaluation": evaluation}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
