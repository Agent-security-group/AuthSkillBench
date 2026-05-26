#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable

try:
    from .runtime import EmailScenario
except ImportError:  # pragma: no cover - supports direct script execution.
    from runtime import EmailScenario


EMAIL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE_PATH = EMAIL_ROOT / "data" / "state.json"
DEFAULT_TOOLKIT_PATH = EMAIL_ROOT / "data" / "toolkits" / "gmail_scenario.json"


def agent_tool_name(native_name: str) -> str:
    """Return a function-name-safe alias for agent frameworks."""

    return native_name.replace(".", "__")


def native_tool_name(name: str) -> str:
    """Accept either native dotted names or framework-safe aliases."""

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


class EmailScenarioAPI:
    """Agent-facing API wrapper around EmailScenario.

    Agents should depend on this wrapper rather than calling EmailScenario
    internals. The wrapper exposes stable tool specs and a single invoke method.
    """

    def __init__(self, state_path: Path = DEFAULT_STATE_PATH, apply_side_effects: bool = True) -> None:
        self.scenario = EmailScenario.load(state_path)
        self.apply_side_effects = apply_side_effects
        self._handlers: dict[str, Callable[[dict[str, Any]], Any]] = {
            "email.search_messages": self._search_messages,
            "email.read_message": self._read_message,
            "email.list_threads": self._list_threads,
            "email.read_thread": self._read_thread,
            "contacts.search": self._search_contacts,
            "contacts.verify_current": self._verify_contact_current,
            "files.list": self._list_files,
            "files.metadata": self._file_metadata,
            "files.read": self._read_file,
            "email.export_messages": self._export_messages,
            "gmail.users.messages.send": self._send_message,
            "gmail.users.messages.forward": self._forward_message,
            "gmail.users.drafts.create": self._create_draft,
            "gmail.users.drafts.update": self._update_draft,
            "gmail.users.drafts.send": self._send_draft,
            "gmail.users.messages.trash": self._trash_message,
            "gmail.users.messages.delete": self._delete_message,
            "gmail.users.messages.batchModify": self._batch_modify_messages,
        }

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

    def manifest(self) -> dict[str, Any]:
        account = self.scenario.state.get("account", {})
        return {
            "schema_version": "authskillbench.email_scenario.api.v1",
            "scenario": "email_scenario",
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
        except Exception as exc:  # Keep the API boundary JSON-only for agents.
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
            "message_count": len(self.scenario.state.get("messages", [])),
            "contact_count": len(self.scenario.state.get("contacts", [])),
            "file_count": len(self.scenario.state.get("files", [])),
            "sent_count": len(self.scenario.state.get("sent", [])),
            "draft_count": len(self.scenario.state.get("drafts", [])),
            "export_count": len(self.scenario.state.get("exports", [])),
            "applied_threat_overlays": self.scenario.state.get("applied_threat_overlays", []),
            "trace": self.scenario.public_trace(),
        }

    def _search_messages(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.search_messages(query=str(arguments.get("query", "")))

    def _read_message(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.read_message(message_id=str(arguments["message_id"]))

    def _list_threads(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.list_threads(query=str(arguments.get("query", "")))

    def _read_thread(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.read_thread(thread_id=str(arguments["thread_id"]))

    def _search_contacts(self, arguments: dict[str, Any]) -> Any:
        approved = arguments.get("approved")
        if approved is not None and not isinstance(approved, bool):
            approved = str(approved).lower() == "true"
        relationship = arguments.get("relationship")
        return self.scenario.search_contacts(
            query=str(arguments.get("query", "")),
            relationship=str(relationship) if relationship else None,
            approved=approved,
        )

    def _verify_contact_current(self, arguments: dict[str, Any]) -> Any:
        purpose = arguments.get("purpose")
        return self.scenario.verify_contact_current(
            email=str(arguments["email"]),
            purpose=str(purpose) if purpose else None,
        )

    def _list_files(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.list_files(include_sensitive=bool(arguments.get("include_sensitive", False)))

    def _file_metadata(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.file_metadata(path=str(arguments["path"]))

    def _read_file(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.read_file(path=str(arguments["path"]))

    def _export_messages(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.export_messages(
            message_ids=arguments.get("message_ids", []),
            destination=str(arguments["destination"]),
            include_attachments=bool(arguments.get("include_attachments", False)),
            apply=self.apply_side_effects,
        )

    def _send_message(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.send_message(apply=self.apply_side_effects, **arguments)

    def _forward_message(self, arguments: dict[str, Any]) -> Any:
        args = dict(arguments)
        message_id = str(args.pop("message_id", args.pop("id", "")))
        to = args.pop("to", [])
        return self.scenario.forward_message(message_id=message_id, to=to, apply=self.apply_side_effects, **args)

    def _create_draft(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.create_draft(apply=self.apply_side_effects, **arguments)

    def _update_draft(self, arguments: dict[str, Any]) -> Any:
        args = dict(arguments)
        draft_id = str(args.pop("draft_id", args.pop("id", "")))
        return self.scenario.update_draft(draft_id=draft_id, apply=self.apply_side_effects, **args)

    def _send_draft(self, arguments: dict[str, Any]) -> Any:
        args = dict(arguments)
        draft_id = str(args.pop("draft_id", args.pop("id", "")))
        return self.scenario.send_draft(draft_id=draft_id, apply=self.apply_side_effects, **args)

    def _trash_message(self, arguments: dict[str, Any]) -> Any:
        args = dict(arguments)
        message_id = str(args.pop("message_id", args.pop("id", "")))
        return self.scenario.trash_message(message_id=message_id, apply=self.apply_side_effects, **args)

    def _delete_message(self, arguments: dict[str, Any]) -> Any:
        args = dict(arguments)
        message_id = str(args.pop("message_id", args.pop("id", "")))
        return self.scenario.delete_message(message_id=message_id, apply=self.apply_side_effects, **args)

    def _batch_modify_messages(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.batch_modify_messages(
            ids=arguments.get("ids", []),
            add_labels=arguments.get("add_labels", arguments.get("addLabelIds", [])),
            remove_labels=arguments.get("remove_labels", arguments.get("removeLabelIds", [])),
            apply=self.apply_side_effects,
        )


def _json_arg(value: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc
    if not isinstance(parsed, dict):
        raise argparse.ArgumentTypeError("--arguments must be a JSON object")
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser(description="Agent-facing API for the AuthSkillBench email scenario.")
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE_PATH)
    parser.add_argument("--dry-run", action="store_true", help="Preview side effects instead of mutating scenario state.")
    parser.add_argument("--manifest", action="store_true", help="Print the agent scenario manifest.")
    parser.add_argument("--openai-tools", action="store_true", help="Print OpenAI-style function tool specs.")
    parser.add_argument("--call", help="Invoke a tool by native name or agent-safe alias.")
    parser.add_argument("--arguments", type=_json_arg, default={}, help="JSON object arguments for --call.")
    args = parser.parse_args()

    api = EmailScenarioAPI(state_path=args.state, apply_side_effects=not args.dry_run)
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
