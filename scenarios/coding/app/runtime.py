from __future__ import annotations
import copy, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def _upsert(items, key, value, item):
    for i, x in enumerate(items):
        if str(x.get(key)) == value:
            merged = copy.deepcopy(x)
            merged.update(copy.deepcopy(item))
            items[i] = merged
            return
    items.append(copy.deepcopy(item))

class CodingScenario:
    def __init__(self, state):
        self.state = state

    @classmethod
    def load(cls, path):
        with path.open("r", encoding="utf-8-sig") as f:
            return cls(json.load(f))

    # ── helpers ──
    def _f(self): return self.state.setdefault("file_contents", [])
    def _prs(self): return self.state.setdefault("pull_requests", [])
    def _iss(self): return self.state.setdefault("issues", [])
    def _ci(self): return self.state.setdefault("ci_logs", {})
    def _co(self): return self.state.setdefault("codeowners", {})
    def _deps(self): return self.state.setdefault("dependencies", [])
    def _keys(self): return self.state.setdefault("ssh_keys", [])
    def _notifs(self): return self.state.setdefault("notifications", [])
    def _acc(self): return self.state.setdefault("account", {})

    def _find_file(self, path):
        for f in self._f():
            if f["path"] == path: return f
        return None

    # ── file ops ──
    def list_files(self, dir):
        return [{"path": f["path"]} for f in self._f() if f["path"].startswith(dir)]
    def read_file(self, path):
        f = self._find_file(path)
        if f is None: raise KeyError(f"file not found: {path}")
        return f
    def write_file(self, path, content):
        _upsert(self._f(), "path", path, {"path": path, "content": content})
        return {"written": path}

    # ── logs ──
    def read_log(self, path): return self.read_file(path)
    def append_log(self, path, msg):
        _upsert(self._f(), "path", path, {"path": path, "content": ""})
        f = self._find_file(path)
        f["content"] += "\n" + msg
        return {"appended": True}

    # ── secrets ──
    def list_keys(self):
        f = self._find_file("/secrets/keys.txt")
        if f is None: return []
        return [{"key": line.split(":")[0].strip()} for line in f["content"].split("\n") if line.strip() and ":" in line and not line.startswith("#")]
    def read_secret(self, key):
        f = self._find_file("/secrets/keys.txt")
        if f is None: raise KeyError("no secrets file")
        for line in f["content"].split("\n"):
            if line.startswith(key + ":"):
                return {"key": key, "value": line.split(":", 1)[1].strip()}
        raise KeyError(f"unknown secret: {key}")

    # ── notifications / ssh keys ──
    def list_notifications(self, filter=None):
        return self._notifs()
    def read_notification(self, nid):
        for n in self._notifs():
            if n["id"] == nid: return n
        raise KeyError(f"notif not found: {nid}")
    def list_ssh_keys(self): return self._keys()
    def add_ssh_key(self, title, key):
        e = {"id": f"key_{len(self._keys())+1:03d}", "title": title, "key": key}
        self._keys().append(e); return e
    def remove_ssh_key(self, kid):
        for i, k in enumerate(self._keys()):
            if k["id"] == kid: return self._keys().pop(i)
        raise KeyError(f"key not found: {kid}")
    def read_account(self): return self._acc()

    # ── PR ops ──
    def read_description(self, pid):
        for p in self._prs():
            if p["id"] == pid: return p
        raise KeyError(f"PR not found: {pid}")
    def read_diff(self, pid): return self.read_description(pid).get("diff", "")
    def list_pr_files(self, pid): return self.read_description(pid).get("changed_files", [])
    def read_pr_comments(self, pid): return self.read_description(pid).get("comments", [])
    def read_pr_reviews(self, pid): return self._co().get(pid, {"approved": False})
    def add_pr_comment(self, pid, body):
        p = self.read_description(pid)
        p.setdefault("comments", []).append({"author": "agent", "body": body})
        return {"added": True}
    def approve_pr(self, pid):
        p = self.read_description(pid); p["state"] = "approved"; return p
    def request_changes(self, pid, comment):
        p = self.read_description(pid); p["state"] = "changes_requested"
        p.setdefault("comments", []).append({"author": "agent", "body": comment})
        return p
    def merge_pr(self, pid):
        co = self._co().get(pid, {})
        if not co.get("approved", False):
            return {"merged": False, "error": "CODEOWNERS not approved"}
        p = self.read_description(pid); p["state"] = "merged"
        return {"merged": True}
    def run_security_scan(self, pid): return {"findings": [], "summary": "ok"}
    def read_file_at_ref(self, path, ref): return self.read_file(path)

    # ── issues ──
    def list_issues(self):
        return [{"id": i["id"], "title": i["title"], "labels": i.get("labels",[]), "state": i.get("state","open")} for i in self._iss()]
    def read_issue(self, iid):
        for i in self._iss():
            if i["id"] == iid: return i
        raise KeyError(f"issue not found: {iid}")
    def add_label(self, iid, label):
        i = self.read_issue(iid); i.setdefault("labels",[]).append(label); return i
    def close_issue(self, iid):
        i = self.read_issue(iid); i["state"] = "closed"; return i

    # ── CI ──
    def read_ci_log(self, pid):
        log = self._ci().get(pid)
        if log is None: raise KeyError(f"no CI log for {pid}")
        return log
    def rerun_ci(self, pid):
        self._ci()[pid] = "[BUILD] OK\n[TEST] 47/47 passed\n[BUILD] CI PASSED"
        return {"rerun": True}

    # ── deps / changelog / releases ──
    def list_deps(self):
        return [{"name": d["name"], "current": d.get("current_version"), "latest": d.get("latest_version")} for d in self._deps()]
    def update_dep(self, name, version):
        for d in self._deps():
            if d["name"] == name: d["current_version"] = version; return {"updated": name, "to": version}
        raise KeyError(f"dep not found: {name}")
    def create_release(self, version, notes): return {"created": version}

    def read_ssh_key(self, kid):
        for k in self._keys():
            if k["id"] == kid: return k
        raise KeyError(f"key not found: {kid}")

    def create_pr(self, branch, title, body):
        pid = f"pr_{len(self._prs())+101}"
        pr = {"id": pid, "branch": branch, "title": title, "body": body, "author": "agent", "state": "open", "ci_status": "pending", "comments": [], "diff": "(auto-generated)"}
        self._prs().append(pr)
        return pr

    # ── threat overlay ──
    def apply_overlay(self, overlay):
        for op in overlay.get("ops", []):
            n = op.get("op")
            if n == "upsert_file_content": _upsert(self._f(), "path", op["file_content"]["path"], op["file_content"])
            elif n == "upsert_file": _upsert(self._f(), "path", op["file"]["path"], op["file"])
            elif n == "upsert_pr": _upsert(self._prs(), "id", op["pr"]["id"], op["pr"])
            elif n == "upsert_issue": _upsert(self._iss(), "id", op["issue"]["id"], op["issue"])
            elif n == "upsert_ci_log": self._ci()[op["ci_log"]["pr_id"]] = op["ci_log"]["log"]
            elif n == "upsert_codeowners": self._co().update(op["codeowners"])
            elif n == "upsert_dependency": _upsert(self._deps(), "name", op["dependency"]["name"], op["dependency"])
            elif n == "upsert_ssh_key": _upsert(self._keys(), "id", op["ssh_key"]["id"], op["ssh_key"])
            elif n == "upsert_notification": _upsert(self._notifs(), "id", op["notification"]["id"], op["notification"])
            elif n == "set_account": self._acc().update(op.get("account", {}))

    def apply_threat_profile(self, profile):
        if profile: self.apply_overlay(profile.get("state_overlay", {}))
