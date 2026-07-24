from __future__ import annotations
import copy, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class CodingRepo:
    def __init__(self, state):
        self.s = state  # state dict reference

    @classmethod
    def load(cls, path):
        with path.open("r", encoding="utf-8-sig") as f:
            return cls(json.load(f))

    # ── helpers ──
    def _next_id(self, prefix):
        n = self.s["next_ids"].setdefault(prefix, 1)
        self.s["next_ids"][prefix] = n + 1
        return f"{prefix}_{n:03d}"

    def _branch_head(self, name):
        b = self.s["branches"].get(name)
        if b is None: raise KeyError(f"branch not found: {name}")
        return b["head"]

    def _set_head(self, name, commit_id):
        self.s["branches"][name]["head"] = commit_id

    def _get_file_snapshot(self, commit_id):
        """Get full file tree at a given commit."""
        snap = self.s["file_snapshots"].get(commit_id, {})
        if snap: return snap
        # Walk back to parent
        c = self.s["commits"].get(commit_id)
        if c is None: return {}
        parent = self._get_file_snapshot(c["parent"])
        snap = copy.deepcopy(parent)
        for fc in c["files"]:
            if fc["new_content"] is None:
                snap.pop(fc["path"], None)
            else:
                snap[fc["path"]] = fc["new_content"]
        self.s["file_snapshots"][commit_id] = snap
        return snap

    def _walk_commits(self, start_id, stop_id=None):
        """Walk commit chain from start back to stop or root."""
        commits = []
        cur = start_id
        while cur and cur != stop_id:
            c = self.s["commits"].get(cur)
            if c is None: break
            commits.append(c)
            cur = c["parent"]
        return commits

    def _generate_diff(self, source_branch, target_branch):
        """Compute real diff between two branch heads."""
        source = self._branch_head(source_branch)
        target = self._branch_head(target_branch)
        if source is None: return ""
        commits = self._walk_commits(source, target)
        lines = []
        for c in reversed(commits):
            for fc in c["files"]:
                lines.append(f"--- a/{fc['path']}")
                lines.append(f"+++ b/{fc['path']}")
                if fc["old_content"] is not None:
                    for l in fc["old_content"].split("\n"):
                        lines.append("-" + l)
                if fc["new_content"] is not None:
                    for l in fc["new_content"].split("\n"):
                        lines.append("+" + l)
        return "\n".join(lines)

    # ── files ──
    def read_file(self, path):
        head = self._branch_head(self.s["current_branch"])
        if head is None: raise KeyError("no commits yet")
        snap = self._get_file_snapshot(head)
        if path not in snap: raise KeyError(f"file not found: {path}")
        return {"path": path, "content": snap[path]}

    def write_file(self, path, content, message=None):
        head = self._branch_head(self.s["current_branch"])
        old = self._get_file_snapshot(head).get(path) if head else None
        cid = self._next_id("commit")
        commit = {
            "id": cid, "parent": head,
            "message": message or f"Update {path}",
            "files": [{"path": path, "old_content": old, "new_content": content}],
            "timestamp": "2026-07-24T00:00:00Z",
        }
        self.s["commits"][cid] = commit
        self._set_head(self.s["current_branch"], cid)
        return {"commit": cid, "path": path, "written": True}

    # ── branch ──
    def list_branches(self):
        return [{"name": n, "head": b.get("head")} for n, b in self.s["branches"].items()]

    def create_branch(self, name, from_branch=None):
        if name in self.s["branches"]: raise KeyError(f"branch exists: {name}")
        src = from_branch or self.s["default_branch"]
        head = self._branch_head(src)
        self.s["branches"][name] = {"head": head, "protected": False}
        return {"branch": name, "from": src}

    def delete_branch(self, name):
        if name == self.s["default_branch"]: raise ValueError("cannot delete default branch")
        if self.s["branches"].pop(name, None) is None: raise KeyError(f"branch not found: {name}")
        return {"deleted": name}

    def switch_branch(self, name):
        if name not in self.s["branches"]: raise KeyError(f"branch not found: {name}")
        self.s["current_branch"] = name
        return {"branch": name}

    # ── commit ──
    def log(self, branch=None):
        head = self._branch_head(branch or self.s["current_branch"])
        cs = self._walk_commits(head)
        return [{"id": c["id"], "message": c["message"], "parent": c["parent"]} for c in cs]

    def show_commit(self, cid):
        c = self.s["commits"].get(cid)
        if c is None: raise KeyError(f"commit not found: {cid}")
        return c

    # ── PR ──
    def create_pr(self, title, body, source_branch, target_branch=None):
        if source_branch not in self.s["branches"]: raise KeyError(f"branch not found: {source_branch}")
        tb = target_branch or self.s["default_branch"]
        pid = self._next_id("pr")
        diff = self._generate_diff(source_branch, tb)
        pr = {
            "id": pid, "title": title, "body": body, "author": "agent",
            "source_branch": source_branch, "target_branch": tb,
            "state": "open", "ci_status": "none",
            "ci_log": "", "reviews": [], "diff": diff,
        }
        self.s["pulls"][pid] = pr
        return pr

    def read_pr(self, pid):
        p = self.s["pulls"].get(pid)
        if p is None: raise KeyError(f"PR not found: {pid}")
        # Refresh diff
        p["diff"] = self._generate_diff(p["source_branch"], p["target_branch"])
        # Check mergeable
        p["mergeable"] = self._check_mergeable(p)
        return p

    def list_prs(self):
        return [{"id": pid, "title": p["title"], "state": p["state"]} for pid, p in self.s["pulls"].items()]

    def read_pr_diff(self, pid):
        return self.read_pr(pid).get("diff", "")

    def add_pr_comment(self, pid, body):
        p = self.s["pulls"].get(pid)
        if p is None: raise KeyError(f"PR not found: {pid}")
        p.setdefault("comments", []).append({"author": "agent", "body": body})
        return {"added": True}

    def approve_pr(self, pid, reviewer="reviewer"):
        p = self.s["pulls"].get(pid)
        if p is None: raise KeyError(f"PR not found: {pid}")
        p.setdefault("reviews", []).append({"reviewer": reviewer, "state": "approved"})
        p["mergeable"] = self._check_mergeable(p)
        return {"approved": True}

    def request_changes_pr(self, pid, reviewer="reviewer", body=""):
        p = self.s["pulls"].get(pid)
        if p is None: raise KeyError(f"PR not found: {pid}")
        p.setdefault("reviews", []).append({"reviewer": reviewer, "state": "changes_requested", "body": body})
        p["mergeable"] = self._check_mergeable(p)
        return {"changes_requested": True}

    def merge_pr(self, pid):
        p = self.s["pulls"].get(pid)
        if p is None: raise KeyError(f"PR not found: {pid}")
        if p["state"] != "open": raise ValueError(f"PR is {p['state']}")
        # Constraints
        if p["ci_status"] not in ("passed", "none"):
            return {"merged": False, "reason": "CI not passed"}
        approvals = [r for r in p.get("reviews", []) if r["state"] == "approved"]
        if not approvals:
            return {"merged": False, "reason": "no approvals"}
        # Fast-forward merge
        sh = self._branch_head(p["source_branch"])
        if sh is None:
            return {"merged": False, "reason": "source branch has no commits"}
        self._set_head(p["target_branch"], sh)
        p["state"] = "merged"
        return {"merged": True, "pr_id": pid}

    def _check_mergeable(self, p):
        if p["state"] != "open": return False
        if p["ci_status"] not in ("passed", "none"): return False
        approvals = [r for r in p.get("reviews", []) if r["state"] == "approved"]
        if not approvals: return False
        return True

    # ── CI ──
    def read_ci_log(self, pid):
        p = self.s["pulls"].get(pid)
        if p is None: raise KeyError(f"PR not found: {pid}")
        return {"log": p.get("ci_log", "No CI log")}

    def rerun_ci(self, pid):
        p = self.s["pulls"].get(pid)
        if p is None: raise KeyError(f"PR not found: {pid}")
        p["ci_status"] = "passed"
        p["ci_log"] = "[TEST] All tests passed\n[BUILD] Build successful"
        return {"ci_status": "passed", "pr_id": pid}

    # ── issues ──
    def list_issues(self):
        return [{"id": iid, "title": i["title"], "state": i["state"]} for iid, i in self.s["issues"].items()]

    def read_issue(self, iid):
        i = self.s["issues"].get(iid)
        if i is None: raise KeyError(f"issue not found: {iid}")
        return i

    def create_issue(self, title, body):
        iid = self._next_id("issue")
        self.s["issues"][iid] = {"id": iid, "title": title, "body": body, "state": "open", "labels": []}
        return self.s["issues"][iid]

    def close_issue(self, iid):
        i = self.s["issues"].get(iid)
        if i is None: raise KeyError(f"issue not found: {iid}")
        i["state"] = "closed"
        return i

    def add_label(self, iid, label):
        i = self.s["issues"].get(iid)
        if i is None: raise KeyError(f"issue not found: {iid}")
        if label not in i.setdefault("labels", []): i["labels"].append(label)
        return i

    # ── release ──
    def create_release(self, version, notes=""):
        head = self._branch_head(self.s["default_branch"])
        rel = {"version": version, "commit": head, "notes": notes}
        self.s.setdefault("releases", []).append(rel)
        return rel

    def list_releases(self):
        return self.s.get("releases", [])

    # ── deps / changelog ──
    def list_deps(self):
        return self.s.get("dependencies", [])
    def update_dep(self, name, version):
        for d in self.s.setdefault("dependencies", []):
            if d["name"] == name: d["version"] = version; return {"updated": name, "to": version}
        self.s["dependencies"].append({"name": name, "version": version})
        return {"added": name, "version": version}

    # ── collaborator / codeowners ──
    def list_collaborators(self): return self.s.get("collaborators", [])
    def add_collaborator(self, username, permission="read"):
        self.s.setdefault("collaborators", []).append({"username": username, "permission": permission})
        return {"added": username}
    def remove_collaborator(self, username):
        self.s["collaborators"] = [c for c in self.s.get("collaborators", []) if c["username"] != username]
        return {"removed": username}

    def check_codeowners(self):
        return self.s.get("codeowners", [])

    # ── threat overlay ──
    def apply_overlay(self, overlay):
        for op in overlay.get("ops", []):
            n = op.get("op")
            if n == "upsert_issue":
                iss = op["issue"]
                self.s["issues"][iss["id"]] = {**self.s["issues"].get(iss["id"], {}), **iss}
            elif n == "upsert_pr":
                pr = op["pr"]
                self.s["pulls"][pr["id"]] = pr
            elif n == "upsert_commit":
                c = op["commit"]
                self.s["commits"][c["id"]] = c
                if c.get("branch"):
                    self._set_head(c["branch"], c["id"])
            elif n == "set_file":
                p = op["path"]
                snap = op.get("snapshot", {})
                self.s.setdefault("file_snapshots", {})[p] = snap
            elif n == "set_ci":
                pr_id = op["pr_id"]
                if pr_id in self.s["pulls"]:
                    self.s["pulls"][pr_id]["ci_status"] = op.get("status", "failed")
                    self.s["pulls"][pr_id]["ci_log"] = op.get("log", "")
            elif n == "set_codeowners":
                self.s["codeowners"] = op.get("rules", [])

    def apply_threat_profile(self, profile):
        if profile: self.apply_overlay(profile.get("state_overlay", {}))