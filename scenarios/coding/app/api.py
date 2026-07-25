from __future__ import annotations
from pathlib import Path
try: from .runtime import CodingRepo
except: from runtime import CodingRepo

ROOT = Path(__file__).resolve().parents[1]
CODING_ROOT = ROOT
DEFAULT_STATE_PATH = ROOT / "data" / "state.json"
DEFAULT_STATE = ROOT / "data" / "state.json"
DEFAULT_TK = ROOT / "data" / "toolkits" / "coding.json"

import json
def load_tk(path=DEFAULT_TK):
    with open(str(path), encoding="utf-8-sig") as f: return json.load(f)
def load_all():
    tk = load_tk()
    specs = []
    for t in tk["tools"]:
        s = dict(t)
        s["agent_name"] = t["name"].replace(".", "__")
        specs.append(s)
    return tk, specs

TK, SPECS = load_all()
TOOLKIT_SPEC = TK
TOOL_SPECS = SPECS

class CodingAPI:
    def __init__(self, sp=DEFAULT_STATE):
        self.repo = CodingRepo.load(sp)

    def otools(self):
        return [{"type":"function","function":{"name":s["agent_name"],"description":s["description"],"parameters":s["parameters"]}} for s in SPECS]

    def invoke(self, tn, args=None):
        n = tn.replace("__", "."); a = args or {}
        h = {
            "files.read": lambda a: {"ok": True, "result": self.repo.read_file(a["path"])},
            "files.write": lambda a: {"ok": True, "result": self.repo.write_file(a["path"], a["content"], a.get("message"), a.get("author", "agent"))},
            "branch.list": lambda a: {"ok": True, "result": self.repo.list_branches()},
            "branch.create": lambda a: {"ok": True, "result": self.repo.create_branch(a["name"], a.get("from"))},
            "branch.delete": lambda a: {"ok": True, "result": self.repo.delete_branch(a["name"])},
            "branch.switch": lambda a: {"ok": True, "result": self.repo.switch_branch(a["name"])},
            "commit.log": lambda a: {"ok": True, "result": self.repo.log(a.get("branch"))},
            "commit.show": lambda a: {"ok": True, "result": self.repo.show_commit(a["commit_id"])},
            "pr.create": lambda a: {"ok": True, "result": self.repo.create_pr(a["title"], a["body"], a["source_branch"], a.get("target_branch"))},
            "pr.list": lambda a: {"ok": True, "result": self.repo.list_prs()},
            "pr.read": lambda a: {"ok": True, "result": self.repo.read_pr(a["pr_id"])},
            "pr.add_comment": lambda a: {"ok": True, "result": self.repo.add_pr_comment(a["pr_id"], a["body"])},
            "pr.approve": lambda a: {"ok": True, "result": self.repo.approve_pr(a["pr_id"])},
            "pr.request_changes": lambda a: {"ok": True, "result": self.repo.request_changes_pr(a["pr_id"], a.get("body",""))},
            "pr.merge": lambda a: {"ok": True, "result": self.repo.merge_pr(a["pr_id"])},
            "ci.read_log": lambda a: {"ok": True, "result": self.repo.read_ci_log(a["pr_id"])},
            "ci.rerun": lambda a: {"ok": True, "result": self.repo.rerun_ci(a["pr_id"])},
            "issues.list": lambda a: {"ok": True, "result": self.repo.list_issues()},
            "issues.read": lambda a: {"ok": True, "result": self.repo.read_issue(a["issue_id"])},
            "issues.create": lambda a: {"ok": True, "result": self.repo.create_issue(a["title"], a["body"])},
            "issues.close": lambda a: {"ok": True, "result": self.repo.close_issue(a["issue_id"])},
            "issues.add_label": lambda a: {"ok": True, "result": self.repo.add_label(a["issue_id"], a["label"])},
            "release.create": lambda a: {"ok": True, "result": self.repo.create_release(a["version"], a.get("notes",""))},
            "release.list": lambda a: {"ok": True, "result": self.repo.list_releases()},
            "deps.list": lambda a: {"ok": True, "result": self.repo.list_deps()},
            "deps.update": lambda a: {"ok": True, "result": self.repo.update_dep(a["name"], a["version"])},
            "collaborator.list": lambda a: {"ok": True, "result": self.repo.list_collaborators()},
            "code.search_files": lambda a: {"ok": True, "result": self.repo.search_files(a["query"])},
"code.search_issues": lambda a: {"ok": True, "result": self.repo.search_issues(a["query"])},
"code.search_commits": lambda a: {"ok": True, "result": self.repo.search_commits(a["query"])},
"code.search_prs": lambda a: {"ok": True, "result": self.repo.search_prs(a["query"])},
"branch.protect": lambda a: {"ok": True, "result": self.repo.protect_branch(a["name"])},
"branch.unprotect": lambda a: {"ok": True, "result": self.repo.unprotect_branch(a["name"])},
"pr.close": lambda a: {"ok": True, "result": self.repo.close_pr(a["pr_id"])},"collaborator.add": lambda a: {"ok": True, "result": self.repo.add_collaborator(a["username"], a.get("permission","read"))},
            "collaborator.remove": lambda a: {"ok": True, "result": self.repo.remove_collaborator(a["username"])},
            "codeowners.check": lambda a: {"ok": True, "result": self.repo.check_codeowners()},
            "pr.close": lambda a: {"ok": True, "result": self.repo.close_pr(a["pr_id"])},
            "code.search_files": lambda a: {"ok": True, "result": self.repo.search_files(a["query"])},
            "code.search_issues": lambda a: {"ok": True, "result": self.repo.search_issues(a["query"])},
            "code.search_commits": lambda a: {"ok": True, "result": self.repo.search_commits(a["query"])},
            "code.search_prs": lambda a: {"ok": True, "result": self.repo.search_prs(a["query"])},
            "branch.protect": lambda a: {"ok": True, "result": self.repo.protect_branch(a["name"])},
            "branch.unprotect": lambda a: {"ok": True, "result": self.repo.unprotect_branch(a["name"])},
        }
        hh = h.get(n)
        if not hh:
            return {"ok": False, "error": f"unknown tool: {tn}"}
        try:
            return hh(a)
        except Exception as e:
            return {"ok": False, "error": str(e)}