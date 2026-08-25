# -*- coding: utf-8 -*-
"""Dry-run validation: build case + messages, verify LLM will see
user_instructions and user_authorization. No network. 0 tokens."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from scenarios.browser.app.mock_web_server import ScenarioWebServer
ScenarioWebServer.shutdown_all()

from _experiment_3x import THREAT_VARIANTS, _build_case
from scenarios.browser.app.agent_runner import build_initial_messages
from scenarios.browser.app.api import TOOL_SPECS
from agent_framework import openai_tools_from_specs

# Pick the adversarial variant for dry-run
vname, threat = THREAT_VARIANTS[2]  # C_adversarial
case = _build_case(vname, threat)
print("=== CASE ===")
print("case_id:", case["case_id"])
print("skill_under_test:", case.get("skill_under_test"))
print("user_authorization:", case.get("user_authorization"))
print()

messages = build_initial_messages(case)
print("=== MESSAGES (sent to LLM) ===")
print("num messages:", len(messages))
for m in messages:
    role = m["role"]
    content = m["content"]
    print("--- role:", role, "---")
    if "user" in role:
        # Parse and pretty-print the JSON payload
        payload = json.loads(content)
        print("  task:", payload.get("task"))
        print("  user_instructions:", payload.get("user_instructions"))
        print("  user_authorization:", json.dumps(payload.get("user_authorization"), indent=4))
        print("  available_skill:", payload.get("available_skill"))
        print("  instructions count:", len(payload.get("instructions", [])))
    else:
        print("  ", content[:200])
print()

# Verify tools
tools = openai_tools_from_specs(TOOL_SPECS)
print("=== TOOLS (sent to LLM) ===")
print("num tools:", len(tools))
for t in tools:
    fn = t.get("function", {})
    print("  -", fn.get("name"))
print()

# Verify threat profile is applied
from scenarios.browser.app.api import BrowserScenarioAPI, DEFAULT_STATE_PATH
import shutil
state_dir = ROOT / "outputs" / "states_3x" / case["case_id"]
state_dir.mkdir(parents=True, exist_ok=True)
state_path = state_dir / "state.json"
if state_path.exists():
    state_path.unlink()
shutil.copy2(str(DEFAULT_STATE_PATH), str(state_path))
api = BrowserScenarioAPI(state_path=state_path, apply_side_effects=False)
api.scenario.apply_threat_profile(case.get("threat_profile"))

# Simulate web_search
search = api.invoke("web_search", {"query": "Example Corp employee portal login"})
print("=== web_search RESULT (what LLM sees) ===")
if search.get("ok"):
    for r in search.get("result", [])[:3]:
        print("  rank", r.get("rank"), "url:", r.get("url"))
        print("    source:", r.get("source"), "trust:", r.get("trust"))
        print("    labels:", r.get("labels"))
        print("    description:", r.get("description", "")[:80])
print()

# Verify safety_check reveals the truth
safety = api.invoke("safety_check_url", {"url": "https://phishing-attacker.com/corp-release"})
print("=== safety_check_url RESULT ===")
if safety.get("ok"):
    r = safety.get("result", {})
    print("  is_safe:", r.get("is_safe"))
    print("  checks:", r.get("checks"))
print()
print("=== DRY-RUN COMPLETE. No HTTP sent. 0 tokens spent. ===")
