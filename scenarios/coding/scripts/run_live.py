import sys, json, argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from agent_framework import OpenAIChatCompletionsClient
from scenarios.coding.app.agent_runner import run_live_agent_case, write_live_trajectories
from scenarios.coding.app.benchmark import iter_case_specs

parser = argparse.ArgumentParser()
parser.add_argument("--case", default="coding_dev_basic")
parser.add_argument("--model", default="deepseek-v4-pro")
parser.add_argument("--max-turns", type=int, default=25)
args = parser.parse_args()

API_KEY = "sk-3d0bf4f717cb4950979a9205ffe18786"
BASE_URL = "https://api.deepseek.com"
client = OpenAIChatCompletionsClient(model=args.model, base_url=BASE_URL, api_key=API_KEY, temperature=0.0)

group, variant = iter_case_specs(selected=[args.case])[0]
print(f"Running: {variant['case_id']}")
print(f"  task:   {variant['task_variant_ref']}")
print(f"  threat: {variant['threat_profile_ref']}")
print(f"  max_turns: {args.max_turns}")
print()

traj = run_live_agent_case(group, variant, client=client, max_turns=args.max_turns)
try:
    from ..app.trajectory import DEFAULT_TRAJECTORIES_DIR
except ImportError:
    from scenarios.coding.app.trajectory import DEFAULT_TRAJECTORIES_DIR
out_dir = DEFAULT_TRAJECTORIES_DIR
out_dir.mkdir(parents=True, exist_ok=True)
write_live_trajectories([traj], out_dir)

print(f"Trajectory written to: {out_dir}")
print(f"Steps: {len(traj['steps'])}")
final = traj.get("final_message")
if isinstance(final, dict):
    print(f"Final: {(final.get('content') or '')[:200]}")
elif isinstance(final, str):
    print(f"Final: {final[:200]}")
else:
    print(f"Final type: {type(final)}")

print()
for i, s in enumerate(traj["steps"]):
    for tc in s.get("tool_calls", []):
        fn = tc.get("function", {}).get("name", "?").replace("__", ".")
        print(f"  [{i}] {fn}")
