from __future__ import annotations
from pathlib import Path
try: from .runtime import CodingScenario
except: from runtime import CodingScenario

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE = ROOT / "data" / "state.json"
DEFAULT_TK = ROOT / "data" / "toolkits" / "github_scenario.json"

import json
def load_ts(path=DEFAULT_TK):
    with open(str(path), encoding="utf-8-sig") as f: return json.load(f)
def all_tools(dir=ROOT/"data"/"toolkits"):
    tools, seen = [], set()
    for fp in sorted(dir.glob("*.json")):
        for t in json.load(open(str(fp), encoding="utf-8-sig")).get("tools", []):
            if t["name"] not in seen:
                seen.add(t["name"])
                t.setdefault("agent_name", t["name"].replace(".", "__"))
                tools.append(t)
    return tools, load_ts()
TOOLS, TK = all_tools()
SPECS = TOOLS

class CodingAPI:
    def __init__(self, sp=DEFAULT_STATE):
        self.sc = CodingScenario.load(sp)

    def otools(self):
        return [{"type":"function","function":{"name":s["agent_name"],"description":s["description"],"parameters":s["parameters"]}} for s in SPECS]

    def invoke(self, tn, args=None):
        n = tn.replace("__", "."); a = args or {}
        h = {
            "config.list_files": lambda a: self.sc.list_files(a["directory"]),
            "config.read_file": lambda a: self.sc.read_file(a["path"]),
            "logs.read": lambda a: self.sc.read_log(a["path"]),
            "logs.append": lambda a: self.sc.append_log(a["path"], a["message"]),
            "secrets.list_keys": lambda a: self.sc.list_keys(),
            "secrets.read_value": lambda a: self.sc.read_secret(a["key"]),
            "files.read": lambda a: self.sc.read_file(a["path"]),
            "files.write": lambda a: self.sc.write_file(a["path"], a["content"]),
            "notifications.list": lambda a: self.sc.list_notifications(),
            "notifications.read": lambda a: self.sc.read_notification(a["notification_id"]),
            "ssh_key.list": lambda a: self.sc.list_ssh_keys(),
            "ssh_key.read": lambda a: self.sc.read_ssh_key(a["key_id"]),
            "ssh_key.add": lambda a: self.sc.add_ssh_key(a["title"], a["key"]),
            "ssh_key.remove": lambda a: self.sc.remove_ssh_key(a["key_id"]),
            "account.read_settings": lambda a: self.sc.read_account(),
            "pr.read_description": lambda a: self.sc.read_description(a["pr_id"]),
            "pr.read_diff": lambda a: self.sc.read_diff(a["pr_id"]),
            "pr.list_files": lambda a: self.sc.list_pr_files(a["pr_id"]),
            "pr.read_file_content": lambda a: self.sc.read_file(a["path"]),
            "pr.read_file_at_ref": lambda a: self.sc.read_file_at_ref(a["path"], a["ref"]),
            "pr.read_comments": lambda a: self.sc.read_pr_comments(a["pr_id"]),
            "pr.read_reviews": lambda a: self.sc.read_pr_reviews(a["pr_id"]),
            "pr.run_security_scan": lambda a: self.sc.run_security_scan(a["pr_id"]),
            "pr.approve": lambda a: self.sc.approve_pr(a["pr_id"]),
            "pr.request_changes": lambda a: self.sc.request_changes(a["pr_id"], a.get("comment","")),
            "pr.merge": lambda a: self.sc.merge_pr(a["pr_id"]),
            "pr.add_comment": lambda a: self.sc.add_pr_comment(a["pr_id"], a["body"]),
            "pr.create": lambda a: self.sc.create_pr(a["branch"], a["title"], a["body"]),
            "issues.list": lambda a: self.sc.list_issues(),
            "issues.read": lambda a: self.sc.read_issue(a["issue_id"]),
            "issues.add_label": lambda a: self.sc.add_label(a["issue_id"], a["label"]),
            "issues.close": lambda a: self.sc.close_issue(a["issue_id"]),
            "ci.read_log": lambda a: self.sc.read_ci_log(a["pr_id"]),
            "ci.rerun": lambda a: self.sc.rerun_ci(a["pr_id"]),
            "codeowners.check": lambda a: self.sc.read_pr_reviews(a["pr_id"]),
            "deps.list": lambda a: self.sc.list_deps(),
            "deps.update": lambda a: self.sc.update_dep(a["name"], a["version"]),
            "changelog.update": lambda a: self.sc.write_file("CHANGELOG.md", a["content"]),
            "releases.create": lambda a: self.sc.create_release(a["version"], a.get("notes","")),
        }
        hh = h.get(n)
        if not hh: return {"ok": False, "error": f"unknown: {tn}"}
        try: return {"ok": True, "tool": n, "arguments": a, "result": hh(a)}
        except Exception as e: return {"ok": False, "tool": n, "error": str(e)}