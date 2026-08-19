#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable

try:
    from .runtime import CodingRepo
except ImportError:  # pragma: no cover - supports direct script execution.
    from runtime import CodingRepo


CODING_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE_PATH = CODING_ROOT / "data" / "state.json"
DEFAULT_TOOLKIT_PATH = CODING_ROOT / "data" / "toolkits" / "coding.json"


def agent_tool_name(native_name: str) -> str:
    """Return a function-name-safe alias for agent frameworks."""

    return native_name.replace(".", "__")


def native_tool_name(name: str) -> str:
    """Accept either native dotted names or framework-safe aliases."""

    return name.replace("__", ".")


def load_toolkit(path: Path = DEFAULT_TOOLKIT_PATH) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as f:
        toolkit = json.load(f)
    if not isinstance(toolkit, dict) or not isinstance(toolkit.get("tools"), list):
        raise ValueError(f"invalid toolkit spec: {path}")
    return toolkit


def load_tool_specs(path: Path = DEFAULT_TOOLKIT_PATH) -> list[dict[str, Any]]:
    toolkit = load_toolkit(path)
    specs: list[dict[str, Any]] = []
    for tool in toolkit["tools"]:
        if not isinstance(tool, dict) or not isinstance(tool.get("name"), str):
            raise ValueError(f"invalid tool spec in {path}")
        spec = dict(tool)
        spec.setdefault("agent_name", agent_tool_name(spec["name"]))
        specs.append(spec)
    return specs


TOOLKIT_SPEC = load_toolkit()
TOOL_SPECS = load_tool_specs()


class CodingAPI:
    """Agent-facing API wrapper around CodingRepo.

    Agents should depend on this wrapper rather than calling CodingRepo
    internals. The wrapper exposes stable tool specs and a single invoke method.
    """

    def __init__(self, state_path: Path = DEFAULT_STATE_PATH) -> None:
        self.repo = CodingRepo.load(state_path)
        self._trace: list[dict[str, Any]] = []

    def list_tools(self) -> list[dict[str, Any]]:
        return [dict(spec) for spec in TOOL_SPECS]

    def openai_tools(self) -> list[dict[str, Any]]:
        """Return function-call tool specs using safe names without dots."""

        tools: list[dict[str, Any]] = []
        for spec in TOOL_SPECS:
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": spec["agent_name"],
                        "description": spec["description"],
                        "parameters": spec["parameters"],
                    },
                }
            )
        return tools

    def otools(self) -> list[dict[str, Any]]:
        """Backward-compatible alias for openai_tools()."""

        return self.openai_tools()

    def manifest(self) -> dict[str, Any]:
        repo = self.repo.s
        return {
            "schema_version": "authskillbench.coding_scenario.api.v1",
            "scenario": "coding_scenario",
            "snapshot_id": repo.get("snapshot_id"),
            "repository": {
                "default_branch": repo.get("default_branch"),
                "current_branch": repo.get("current_branch"),
                "protected_branches": [
                    name
                    for name, branch in repo.get("branches", {}).items()
                    if branch.get("protected")
                ],
            },
            "toolkit": {
                "toolkit_id": TOOLKIT_SPEC.get("toolkit_id"),
                "name_for_model": TOOLKIT_SPEC.get("name_for_model"),
                "description_for_model": TOOLKIT_SPEC.get("description_for_model"),
            },
            "tools": self.list_tools(),
        }

    def snapshot(self) -> dict[str, Any]:
        repo = self.repo.s
        return {
            "branch_count": len(repo.get("branches", {})),
            "commit_count": len(repo.get("commits", {})),
            "pr_count": len(repo.get("pulls", {})),
            "issue_count": len(repo.get("issues", {})),
            "release_count": len(repo.get("releases", [])),
            "collaborator_count": len(repo.get("collaborators", [])),
            "dependency_count": len(repo.get("dependencies", [])),
            "applied_threat_overlays": repo.get("applied_threat_overlays", []),
            "trace": self.public_trace(),
        }

    def public_trace(self) -> list[dict[str, Any]]:
        return [dict(entry) for entry in self._trace]

    def invoke(self, tool_name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        native_name = native_tool_name(tool_name)
        args = arguments or {}
        handler = self._handlers().get(native_name)
        if not handler:
            return {
                "ok": False,
                "tool": native_name,
                "error": f"unknown tool: {tool_name}",
                "available_tools": [spec["name"] for spec in TOOL_SPECS],
            }

        try:
            result = handler(args)
        except Exception as exc:  # Keep the API boundary JSON-only for agents.
            return {"ok": False, "tool": native_name, "arguments": args, "error": str(exc)}

        self._trace.append({"tool": native_name, "arguments": args, "result": result})
        return {
            "ok": True,
            "tool": native_name,
            "arguments": args,
            "result": result,
            "trace": self.public_trace(),
        }

    def _handlers(self) -> dict[str, Callable[[dict[str, Any]], Any]]:
        return {
            "files.read": lambda a: self.repo.read_file(a["path"]),
            "files.write": lambda a: self.repo.write_file(a["path"], a["content"], a.get("message"), a.get("author", "agent")),
            "branch.list": lambda a: self.repo.list_branches(),
            "branch.create": lambda a: self.repo.create_branch(a["name"], a.get("from")),
            "branch.delete": lambda a: self.repo.delete_branch(a["name"]),
            "branch.switch": lambda a: self.repo.switch_branch(a["name"]),
            "branch.protect": lambda a: self.repo.protect_branch(a["name"]),
            "branch.unprotect": lambda a: self.repo.unprotect_branch(a["name"]),
            "commit.log": lambda a: self.repo.log(a.get("branch")),
            "commit.show": lambda a: self.repo.show_commit(a["commit_id"]),
            "pr.create": lambda a: self.repo.create_pr(a["title"], a["body"], a["source_branch"], a.get("target_branch")),
            "pr.list": lambda a: self.repo.list_prs(),
            "pr.read": lambda a: self.repo.read_pr(a["pr_id"]),
            "pr.add_comment": lambda a: self.repo.add_pr_comment(a["pr_id"], a["body"]),
            "pr.approve": lambda a: self.repo.approve_pr(a["pr_id"]),
            "pr.request_changes": lambda a: self.repo.request_changes_pr(a["pr_id"], a.get("body", "")),
            "pr.merge": lambda a: self.repo.merge_pr(a["pr_id"]),
            "pr.close": lambda a: self.repo.close_pr(a["pr_id"]),
            "ci.read_log": lambda a: self.repo.read_ci_log(a["pr_id"]),
            "ci.rerun": lambda a: self.repo.rerun_ci(a["pr_id"]),
            "issues.list": lambda a: self.repo.list_issues(),
            "issues.read": lambda a: self.repo.read_issue(a["issue_id"]),
            "issues.create": lambda a: self.repo.create_issue(a["title"], a["body"]),
            "issues.close": lambda a: self.repo.close_issue(a["issue_id"]),
            "issues.add_label": lambda a: self.repo.add_label(a["issue_id"], a["label"]),
            "release.create": lambda a: self.repo.create_release(a["version"], a.get("notes", "")),
            "release.list": lambda a: self.repo.list_releases(),
            "deps.list": lambda a: self.repo.list_deps(),
            "deps.update": lambda a: self.repo.update_dep(a["name"], a["version"]),
            "collaborator.list": lambda a: self.repo.list_collaborators(),
            "collaborator.add": lambda a: self.repo.add_collaborator(a["username"], a.get("permission", "read")),
            "collaborator.remove": lambda a: self.repo.remove_collaborator(a["username"]),
            "codeowners.check": lambda a: self.repo.check_codeowners(),
            "code.search_files": lambda a: self.repo.search_files(a["query"]),
            "code.search_issues": lambda a: self.repo.search_issues(a["query"]),
            "code.search_commits": lambda a: self.repo.search_commits(a["query"]),
            "code.search_prs": lambda a: self.repo.search_prs(a["query"]),
        }


def _json_arg(value: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc
    if not isinstance(parsed, dict):
        raise argparse.ArgumentTypeError("--arguments must be a JSON object")
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser(description="Agent-facing API for the AuthSkillBench coding scenario.")
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE_PATH)
    parser.add_argument("--manifest", action="store_true", help="Print the agent scenario manifest.")
    parser.add_argument("--openai-tools", action="store_true", help="Print OpenAI-style function tool specs.")
    parser.add_argument("--call", help="Invoke a tool by native name or agent-safe alias.")
    parser.add_argument("--arguments", type=_json_arg, default={}, help="JSON object arguments for --call.")
    args = parser.parse_args()

    api = CodingAPI(state_path=args.state)
    if args.openai_tools:
        print(json.dumps(api.openai_tools(), indent=2, sort_keys=False))
        return 0
    if args.manifest or not args.call:
        print(json.dumps(api.manifest(), indent=2, sort_keys=False))
        return 0

    print(json.dumps(api.invoke(args.call, args.arguments), indent=2, sort_keys=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
