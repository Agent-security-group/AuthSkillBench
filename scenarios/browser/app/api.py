#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable

try:
    from .runtime import BrowserScenario
except ImportError:
    from runtime import BrowserScenario


BROWSER_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE_PATH = BROWSER_ROOT / "data" / "state.json"
DEFAULT_TOOLKIT_PATH = BROWSER_ROOT / "data" / "toolkits" / "browser_scenario.json"


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


class BrowserScenarioAPI:
    """Agent-facing API wrapper around BrowserScenario.

    Agents should depend on this wrapper rather than calling BrowserScenario
    internals. The wrapper exposes stable tool specs and a single invoke method.
    """

    def __init__(self, state_path: Path = DEFAULT_STATE_PATH, apply_side_effects: bool = True) -> None:
        self.scenario = BrowserScenario.load(state_path)
        self.apply_side_effects = apply_side_effects
        self._handlers: dict[str, Callable[[dict[str, Any]], Any]] = {
            "web_search": self._web_search,
            "fetch_url": self._fetch_url,
            "api_test_health": self._api_test_health,
            "extract_content": self._extract_content,
            "fetch_web_page": self._fetch_web_page,
            "read_cached_page": self._read_cached_page,
            "list_cached_pages": self._list_cached_pages,
            "check_url_safety": self._check_url_safety,
            "list_downloaded_files": self._list_downloaded_files,
            "get_page_metadata": self._get_page_metadata,
            "clear_cookies": self._clear_cookies,
        }

    def list_tools(self) -> list[dict[str, Any]]:
        supported = {"web_search", "fetch_url", "extract_content", "read_cached_page", "check_url_safety"}
        return [dict(spec) for spec in TOOL_SPECS if spec["name"] in supported]

    def openai_tools(self) -> list[dict[str, Any]]:
        tools: list[dict[str, Any]] = []
        for spec in self.list_tools():
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
            "schema_version": "authskillbench.browser_scenario.api.v1",
            "scenario": "browser_scenario",
            "snapshot_id": self.scenario.state.get("snapshot_id"),
            "account": {
                "userId": account.get("userId", "me"),
                "email": account.get("email"),
                "display_name": account.get("display_name"),
                "organization_domains": account.get("organization_domains", []),
            },
            "apply_side_effects": self.apply_side_effects,
            "toolkit": {
                "toolkit_id": TOOLKIT_SPEC.get("toolkit_id"),
                "name_for_model": TOOLKIT_SPEC.get("name_for_model"),
                "description_for_model": TOOLKIT_SPEC.get("description_for_model"),
            },
            "tools": self.list_tools(),
            "unsupported_tools": [s["name"] for s in TOOL_SPECS if s["name"] not in {t["name"] for t in self.list_tools()}],
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
        return self.scenario.snapshot()

    def _web_search(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.search_web(
            query=str(arguments.get("query", "")),
            num_results=int(arguments.get("max_results", arguments.get("num_results", 5))),
        )

    def _fetch_url(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.fetch_url_content(
            url=str(arguments["url"]),
            include_html=bool(arguments.get("include_html", False)),
            max_length=int(arguments.get("max_length", 50000)),
            include_internal_cookies=bool(arguments.get("include_internal_cookies", False)),
        )

    def _api_test_health(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.fetch_url_content(url=str(arguments["url"]), include_html=False, max_length=1000)

    def _extract_content(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.fetch_url_content(
            url=str(arguments["url"]),
            include_html=bool(arguments.get("extract_type") == "full"),
            max_length=int(arguments.get("max_length", 50000)),
            include_internal_cookies=False,
        )

    def _fetch_web_page(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.fetch_web_page(
            target_url=str(arguments["target_url"]),
            extract_full_text=bool(arguments.get("extract_full_text", False)),
            download_attachments=bool(arguments.get("download_attachments", False)),
            include_internal_cookies=bool(arguments.get("include_internal_cookies", False)),
            apply=self.apply_side_effects,
        )

    def _read_cached_page(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.read_cached_page(target_url=str(arguments["target_url"]))

    def _list_cached_pages(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.list_cached_pages()

    def _check_url_safety(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.check_url_safety(url=str(arguments["url"]))

    def _list_downloaded_files(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.list_downloaded_files()

    def _get_page_metadata(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.get_page_metadata(url=str(arguments["url"]))

    def _clear_cookies(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.clear_cookies(apply=self.apply_side_effects)


def _json_arg(value: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc
    if not isinstance(parsed, dict):
        raise argparse.ArgumentTypeError("--arguments must be a JSON object")
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser(description="Agent-facing API for the AuthSkillBench browser scenario.")
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE_PATH)
    parser.add_argument("--dry-run", action="store_true", help="Preview side effects instead of mutating scenario state.")
    parser.add_argument("--manifest", action="store_true", help="Print the agent scenario manifest.")
    parser.add_argument("--openai-tools", action="store_true", help="Print OpenAI-style function tool specs.")
    parser.add_argument("--call", help="Invoke a tool by native name or agent-safe alias.")
    parser.add_argument("--arguments", type=_json_arg, default={}, help="JSON object arguments for --call.")
    args = parser.parse_args()

    api = BrowserScenarioAPI(state_path=args.state, apply_side_effects=not args.dry_run)
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
