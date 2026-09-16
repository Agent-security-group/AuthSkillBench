#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable

try:
    from .runtime import WorkspaceScenario
except ImportError:
    from runtime import WorkspaceScenario


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE_PATH = WORKSPACE_ROOT / "data" / "state.json"
DEFAULT_TOOLKIT_PATH = WORKSPACE_ROOT / "data" / "toolkits" / "workspace_scenario.json"


def agent_tool_name(native_name: str) -> str:
    return native_name.replace(".", "__")


def native_tool_name(name: str) -> str:
    return name.replace("__", ".")


def load_toolkit(path: Path = DEFAULT_TOOLKIT_PATH) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
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


class WorkspaceScenarioAPI:
    """Agent-facing API wrapper around WorkspaceScenario."""

    def __init__(self, state_path: Path = DEFAULT_STATE_PATH, apply_side_effects: bool = True) -> None:
        self.scenario = WorkspaceScenario.load(state_path)
        self.apply_side_effects = apply_side_effects
        self._handlers: dict[str, Callable[[dict[str, Any]], Any]] = {
            "files.search": self._search_files,
            "files.read": self._read_file,
            "files.metadata": self._file_metadata,
            "files.list_folder": self._list_folder,
            "files.version_history": self._version_history,
            "files.create": self._create_file,
            "files.edit": self._edit_file,
            "files.copy": self._copy_file,
            "files.move": self._move_file,
            "files.delete": self._delete_file,
            "files.archive": self._archive_file,
            "files.export": self._export_file,
            "files.share": self._share_file,
            "files.create_archive": self._create_archive,
            "files.create_folder": self._create_folder,
            "members.search": self._search_members,
            "members.get_permissions": self._get_member_permissions,
        }

    def list_tools(self) -> list[dict[str, Any]]:
        return [dict(spec) for spec in TOOL_SPECS]

    def openai_tools(self) -> list[dict[str, Any]]:
        tools: list[dict[str, Any]] = []
        for spec in TOOL_SPECS:
            tools.append({
                "type": "function",
                "function": {
                    "name": spec["agent_name"],
                    "description": spec["description"],
                    "parameters": spec["parameters"],
                },
            })
        return tools

    def manifest(self) -> dict[str, Any]:
        account = self.scenario.state.get("account", {})
        return {
            "schema_version": "authskillbench.workspace_scenario.api.v1",
            "scenario": "workspace_scenario",
            "snapshot_id": self.scenario.state.get("snapshot_id"),
            "account": {
                "userId": account.get("userId", "me"),
                "email": account.get("email"),
                "display_name": account.get("display_name"),
            },
            "apply_side_effects": self.apply_side_effects,
            "toolkit": {
                "toolkit_id": TOOLKIT_SPEC.get("toolkit_id"),
                "name_for_model": TOOLKIT_SPEC.get("name_for_model"),
                "description_for_model": TOOLKIT_SPEC.get("description_for_model"),
            },
            "tools": self.list_tools(),
        }

    def invoke(self, tool_name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        native_name = native_tool_name(tool_name)
        args = arguments or {}
        handler = self._handlers.get(native_name)
        if not handler:
            return {
                "ok": False,
                "tool": native_name,
                "error": f"unknown tool: {tool_name}",
                "available_tools": [spec["name"] for spec in TOOL_SPECS],
            }
        try:
            result = handler(args)
        except PermissionError as exc:
            return {"ok": False, "tool": native_name, "arguments": args, "error": str(exc), "permission_denied": True}
        except Exception as exc:
            return {"ok": False, "tool": native_name, "arguments": args, "error": str(exc)}
        return {
            "ok": True,
            "tool": native_name,
            "arguments": args,
            "result": result,
            "trace": self.scenario.public_trace(),
        }

    def snapshot(self) -> dict[str, Any]:
        return {
            "file_count": len(self.scenario.state.get("files", [])),
            "folder_count": len(self.scenario.state.get("folders", [])),
            "member_count": len(self.scenario.state.get("members", [])),
            "sent_count": len(self.scenario.state.get("sent", [])),
            "applied_threat_overlays": self.scenario.state.get("applied_threat_overlays", []),
            "trace": self.scenario.public_trace(),
        }

    # ── Handler wrappers ─────────────────────────────────────

    def _search_files(self, args: dict[str, Any]) -> Any:
        return self.scenario.search_files(
            query=str(args.get("query", "")),
            folder_id=str(args["folder_id"]) if args.get("folder_id") else None,
            tags=args.get("tags"),
        )

    def _read_file(self, args: dict[str, Any]) -> Any:
        return self.scenario.read_file(file_id=str(args["file_id"]))

    def _file_metadata(self, args: dict[str, Any]) -> Any:
        return self.scenario.file_metadata(file_id=str(args["file_id"]))

    def _list_folder(self, args: dict[str, Any]) -> Any:
        return self.scenario.list_folder(
            folder_id=str(args["folder_id"]),
            include_permissions=bool(args.get("include_permissions", False)),
        )

    def _version_history(self, args: dict[str, Any]) -> Any:
        return self.scenario.version_history(file_id=str(args["file_id"]))

    def _create_file(self, args: dict[str, Any]) -> Any:
        return self.scenario.create_file(
            name=str(args["name"]),
            content=str(args["content"]),
            folder_id=str(args["folder_id"]),
            tags=args.get("tags"),
            apply=self.apply_side_effects,
        )

    def _edit_file(self, args: dict[str, Any]) -> Any:
        return self.scenario.edit_file(
            file_id=str(args["file_id"]),
            content=str(args["content"]) if args.get("content") else None,
            name=str(args["name"]) if args.get("name") else None,
            apply=self.apply_side_effects,
        )

    def _copy_file(self, args: dict[str, Any]) -> Any:
        return self.scenario.copy_file(
            file_id=str(args["file_id"]),
            target_folder_id=str(args["target_folder_id"]),
            new_name=str(args["new_name"]) if args.get("new_name") else None,
            apply=self.apply_side_effects,
        )

    def _move_file(self, args: dict[str, Any]) -> Any:
        return self.scenario.move_file(
            file_id=str(args["file_id"]),
            target_folder_id=str(args["target_folder_id"]),
            apply=self.apply_side_effects,
        )

    def _delete_file(self, args: dict[str, Any]) -> Any:
        return self.scenario.delete_file(
            file_id=str(args["file_id"]),
            permanent=bool(args.get("permanent", False)),
            apply=self.apply_side_effects,
        )

    def _archive_file(self, args: dict[str, Any]) -> Any:
        return self.scenario.archive_file(
            file_id=str(args["file_id"]),
            apply=self.apply_side_effects,
        )

    def _export_file(self, args: dict[str, Any]) -> Any:
        return self.scenario.export_file(
            file_id=str(args["file_id"]),
            destination=str(args["destination"]),
            format=str(args.get("format", "md")),
            apply=self.apply_side_effects,
        )

    def _share_file(self, args: dict[str, Any]) -> Any:
        return self.scenario.share_file(
            file_id=str(args["file_id"]),
            user_email=str(args["user_email"]),
            permissions=args.get("permissions", []),
            apply=self.apply_side_effects,
        )

    def _create_archive(self, args: dict[str, Any]) -> Any:
        return self.scenario.create_archive(
            file_ids=args.get("file_ids", []),
            archive_name=str(args["archive_name"]),
            apply=self.apply_side_effects,
        )

    def _create_folder(self, args: dict[str, Any]) -> Any:
        parent = args.get("parent_id")
        return self.scenario.create_folder(
            name=str(args["name"]),
            parent_id=str(parent) if parent else None,
            apply=self.apply_side_effects,
        )

    def _search_members(self, args: dict[str, Any]) -> Any:
        return self.scenario.search_members(query=str(args.get("query", "")))

    def _get_member_permissions(self, args: dict[str, Any]) -> Any:
        return self.scenario.get_member_permissions(email=str(args["email"]))


def _json_arg(value: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc
    if not isinstance(parsed, dict):
        raise argparse.ArgumentTypeError("--arguments must be a JSON object")
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser(description="Agent-facing API for the AuthSkillBench workspace scenario.")
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE_PATH)
    parser.add_argument("--dry-run", action="store_true", help="Preview side effects instead of mutating scenario state.")
    parser.add_argument("--manifest", action="store_true", help="Print the agent scenario manifest.")
    parser.add_argument("--openai-tools", action="store_true", help="Print OpenAI-style function tool specs.")
    parser.add_argument("--call", help="Invoke a tool by native name or agent-safe alias.")
    parser.add_argument("--arguments", type=_json_arg, default={}, help="JSON object arguments for --call.")
    args = parser.parse_args()

    api = WorkspaceScenarioAPI(state_path=args.state, apply_side_effects=not args.dry_run)
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
