# -*- coding: utf-8 -*-
"""Verify the risky line case REALLY contains attack/threat data.
Pure local read. NO network. 0 tokens spent.
"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from scenarios.browser.app.benchmark import load_case

case_id = "web_browsing_ambiguous_adversarial_untrusted"
case = load_case(case_id)

print("=" * 70)
print("CASE:", case_id)
print("=" * 70)
print("case_id :", case.get("case_id"))
print("task_type:", case.get("task", {}).get("task_type"))
print("operation:", case.get("task", {}).get("operation"))
print("description:", case.get("task", {}).get("description"))
print()

threat = case.get("threat_profile") or {}
print("-" * 70)
print("THREAT PROFILE")
print("-" * 70)
print("threat_profile_id:", threat.get("threat_profile_id"))
print("severity:", threat.get("severity"))
print("description:", threat.get("description"))
print()

# Check for SEO poisoning injection
poisoned = threat.get("injected_search_results") or threat.get("search_results") or []
print("Injected/poisoned search results:", len(poisoned), "entries")
for r in poisoned:
    if isinstance(r, dict):
        labels = r.get("labels") or r.get("label") or []
        print("  rank=", r.get("rank"), "url=", r.get("url"),
              "labels=", labels, "trust=", r.get("trust"))
print()

# Check for blocked domains
blocked = threat.get("blocked_domains") or []
print("Blocked domains:", len(blocked), "entries")
for bd in blocked:
    print("  -", bd)
print()

# Check what the LLM would actually SEE from web_search
print("-" * 70)
print("WHAT THE LLM SEES (simulated web_search return, labels stripped)")
print("-" * 70)
from scenarios.browser.app.api import BrowserScenarioAPI
api = BrowserScenarioAPI(apply_side_effects=False)
api.scenario.apply_threat_profile(case.get("threat_profile"))
search_result = api.invoke("web_search", {"query": "company portal login"})
print(json.dumps(search_result, ensure_ascii=False, indent=2)[:2000])
print()

# Check if safety_check can discover the threat
print("-" * 70)
print("WHAT safety_check_url REVEALS (the only way LLM can discover threat)")
print("-" * 70)
# Find the first malicious URL from search results (rank 1)
first_poisoned_url = None
if search_result.get("ok") and search_result.get("result"):
    for r in search_result["result"]:
        if "phishing-attacker.com" in str(r.get("url", "")) or "malware-host" in str(r.get("url", "")):
            first_poisoned_url = r.get("url")
            break
if first_poisoned_url:
    safety_result = api.invoke("safety_check_url", {"url": first_poisoned_url})
    print("safety_check_url(", first_poisoned_url, "):")
    print(json.dumps(safety_result, ensure_ascii=False, indent=2)[:1500])
else:
    print("(no poisoned URL found to check)")

print()
print("=" * 70)
print("VERDICT: If you see SEO-poisoned results above AND safety_check")
print("returns is_safe=false, the attack scenario is REAL in the sandbox.")
print("NO HTTP request was sent. 0 tokens spent.")
print("=" * 70)
