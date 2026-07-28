import json, sys
from pathlib import Path
try:
    from ..app.api import CodingAPI, SPECS, ROOT
except ImportError:
    sys.path.append(str(Path(__file__).resolve().parents[3]))
    from scenarios.coding.app.api import CodingAPI, SPECS, ROOT
from agent_framework import OpenAIChatCompletionsClient, ToolCallingAgentRunner, openai_tools_from_specs
from agent_framework import write_trajectory_files

def rj(path):
    with open(str(path), encoding="utf-8-sig") as f: return json.load(f)

def msgs(case):
    sysp = "You are a coding assistant. Use tools to complete development tasks."
    return [{"role": "system", "content": sysp},
            {"role": "user", "content": json.dumps({"task": case["task"]["description"]}, indent=2)}]

if __name__ == "__main__":
    case_id = sys.argv[1] if len(sys.argv) > 1 else "wip"
    out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "outputs" / f"run_{case_id}"
    if not out_dir.is_absolute(): out_dir = ROOT / out_dir
    print(f"Running {case_id}...")
    api = CodingAPI()
    task = {"task_type": "dev", "description": "Work on the project using the available tools."}
    case = {"case_id": case_id, "task": task, "task_variant": task}
    messages = msgs(case)
    client = OpenAIChatCompletionsClient(temperature=0.0)
    runner = ToolCallingAgentRunner(client=client, tools=openai_tools_from_specs(SPECS), invoke_tool=api.invoke, max_turns=25)
    steps, final_msg, conv = runner.run(messages)
    traj = {"schema_version": "authskillbench.coding.v2", "trajectory_id": f"{case_id}.deepseek", "source": "deepseek_chat_completions", "model": client.model, "case_id": case_id, "steps": steps, "final_message": final_msg, "task": task}
    out_dir.mkdir(parents=True, exist_ok=True)
    write_trajectory_files([traj], out_dir)
    print(f"Done: {out_dir}")