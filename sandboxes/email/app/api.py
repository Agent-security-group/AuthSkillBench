#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable

try:
    from .runtime import EmailSandbox
except ImportError:  # pragma: no cover - supports direct script execution.
    from runtime import EmailSandbox


EMAIL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE_PATH = EMAIL_ROOT / "data" / "state.json"
DEFAULT_TOOLKIT_PATH = EMAIL_ROOT / "data" / "toolkits" / "gmail_sandbox.json"


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


class EmailSandboxAPI:
    """Agent-facing API wrapper around EmailSandbox.

    Agents should depend on this wrapper rather than calling EmailSandbox
    internals. The wrapper exposes stable tool specs and a single invoke method.
    """

    def __init__(self, state_path: Path = DEFAULT_STATE_PATH, apply_side_effects: bool = True) -> None:
        self.sandbox = EmailSandbox.load(state_path)
        self.apply_side_effects = apply_side_effects
        self._handlers: dict[str, Callable[[dict[str, Any]], Any]] = {
            "email.search_messages": self._search_messages,
            "email.read_message": self._read_message,
            "files.read": self._read_file,
            "gmail.users.messages.send": self._send_message,
            "gmail.users.drafts.create": self._create_draft,
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
        account = self.sandbox.state.get("account", {})
        return {
            "schema_version": "authskillbench.email_sandbox.api.v1",
            "environment": "email_sandbox",
            "snapshot_id": self.sandbox.state.get("snapshot_id"),
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
            "trace": self.sandbox.public_trace(),
        }

    def snapshot(self) -> dict[str, Any]:
        return {
            "sent_count": len(self.sandbox.state.get("sent", [])),
            "draft_count": len(self.sandbox.state.get("drafts", [])),
            "trace": self.sandbox.public_trace(),
        }

    def _search_messages(self, arguments: dict[str, Any]) -> Any:
        return self.sandbox.search_messages(query=str(arguments.get("query", "")))

    def _read_message(self, arguments: dict[str, Any]) -> Any:
        return self.sandbox.read_message(message_id=str(arguments["message_id"]))

    def _read_file(self, arguments: dict[str, Any]) -> Any:
        return self.sandbox.read_file(path=str(arguments["path"]))

    def _send_message(self, arguments: dict[str, Any]) -> Any:
        return self.sandbox.send_message(apply=self.apply_side_effects, **arguments)

    def _create_draft(self, arguments: dict[str, Any]) -> Any:
        return self.sandbox.create_draft(apply=self.apply_side_effects, **arguments)


def _json_arg(value: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc
    if not isinstance(parsed, dict):
        raise argparse.ArgumentTypeError("--arguments must be a JSON object")
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser(description="Agent-facing API for the AuthSkillBench email sandbox.")
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE_PATH)
    parser.add_argument("--dry-run", action="store_true", help="Preview side effects instead of mutating sandbox state.")
    parser.add_argument("--manifest", action="store_true", help="Print the agent environment manifest.")
    parser.add_argument("--openai-tools", action="store_true", help="Print OpenAI-style function tool specs.")
    parser.add_argument("--call", help="Invoke a tool by native name or agent-safe alias.")
    parser.add_argument("--arguments", type=_json_arg, default={}, help="JSON object arguments for --call.")
    args = parser.parse_args()

    api = EmailSandboxAPI(state_path=args.state, apply_side_effects=not args.dry_run)
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
