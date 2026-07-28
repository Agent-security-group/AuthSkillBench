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
    def __init__(self, state_path: Path = DEFAULT_STATE_PATH, apply_side_effects: bool = True) -> None:
        self.scenario = BrowserScenario.load(state_path)
        self.apply_side_effects = apply_side_effects
        self._handlers: dict[str, Callable[[dict[str, Any]], Any]] = {
            "web_search": self._web_search,
            "fetch_url": self._fetch_url,
            "extract_content": self._extract_content,
            "browser_navigate": self._browser_navigate,
            "browser_act": self._browser_act,
            "browser_extract": self._browser_extract,
            "browser_observe": self._browser_observe,
            "browser_screenshot": self._browser_screenshot,
            "browser_close": self._browser_close,
            "http_request": self._http_request,
            "http_debug": self._http_debug,
            "http_security": self._http_security,
            "fetch_webpage_jina": self._fetch_webpage_jina,
            "fetch_webpage_markdown": self._fetch_webpage_markdown,
            "fetch_webpage_defuddle": self._fetch_webpage_defuddle,
            "extract_web_content": self._extract_web_content,
            "extract_and_summarize": self._extract_and_summarize,
            "read_cached_page": self._read_cached_page,
            "list_cached_pages": self._list_cached_pages,
            "check_url_safety": self._check_url_safety,
            "clear_cookies": self._clear_cookies,
            "api_test_request": self._api_test_request,
            "api_test_health": self._api_test_health,
            "api_test_json": self._api_test_json,
            "automation_navigate": self._automation_navigate,
            "automation_click": self._automation_click,
            "automation_input": self._automation_input,
            "automation_scroll": self._automation_scroll,
            "automation_download": self._automation_download,
            "automation_content": self._automation_content,
            "safety_check_url": self._safety_check_url,
            "safety_check_file": self._safety_check_file,
            "safety_scan_content": self._safety_scan_content,
            "security_scan_port": self._security_scan_port,
            "security_scan_vulnerability": self._security_scan_vulnerability,
            "security_scan_ssl": self._security_scan_ssl,
            "security_audit": self._security_audit,
            "dns_query": self._dns_query,
            "dns_debug": self._dns_debug,
            "network_connectivity": self._network_connectivity,
            "proxy_test": self._proxy_test,
            "browser_use_open": self._browser_use_open,
            "browser_use_state": self._browser_use_state,
            "browser_use_click": self._browser_use_click,
            "browser_use_input": self._browser_use_input,
            "browser_use_screenshot": self._browser_use_screenshot,
            "browser_use_cookies": self._browser_use_cookies,
            "fetch_web_page": self._fetch_web_page,
            "list_downloaded_files": self._list_downloaded_files,
            "get_page_metadata": self._get_page_metadata,
        }

    def list_tools(self) -> list[dict[str, Any]]:
        return [dict(spec) for spec in TOOL_SPECS]

    def openai_tools(self) -> list[dict[str, Any]]:
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
        return {
            "visited_pages_count": len(self.scenario.state.get("visited_pages", [])),
            "downloaded_files_count": len(self.scenario.state.get("downloaded_files", [])),
            "cached_pages_count": len(self.scenario.state.get("cached_pages", [])),
            "search_results_count": len(self.scenario.state.get("search_results", [])),
            "applied_threat_overlays": self.scenario.state.get("applied_threat_overlays", []),
            "trace": self.scenario.public_trace(),
        }

    def _web_search(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.search_web(
            query=str(arguments["query"]),
            num_results=int(arguments.get("max_results", 5)),
        )

    def _fetch_url(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.fetch_url(
            url=str(arguments["url"]),
            include_html=bool(arguments.get("include_html", False)),
            max_length=int(arguments.get("max_length", 50000)),
        )

    def _extract_content(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.extract_content(
            url=str(arguments["url"]),
            extract_type=str(arguments.get("extract_type", "summary")),
        )

    def _browser_navigate(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.browser_navigate(
            url=str(arguments["url"]),
            session_name=arguments.get("session_name"),
        )

    def _browser_act(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.browser_act(
            action=str(arguments["action"]),
            session_name=arguments.get("session_name"),
        )

    def _browser_extract(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.browser_extract(
            instruction=str(arguments["instruction"]),
            schema=arguments.get("schema"),
            session_name=arguments.get("session_name"),
        )

    def _browser_observe(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.browser_observe(
            query=str(arguments["query"]),
            session_name=arguments.get("session_name"),
        )

    def _browser_screenshot(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.browser_screenshot(
            session_name=arguments.get("session_name"),
            full_page=bool(arguments.get("full_page", False)),
        )

    def _browser_close(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.browser_close(session_name=arguments.get("session_name"))

    def _http_request(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.http_request(
            url=str(arguments["url"]),
            method=str(arguments.get("method", "GET")),
            headers=arguments.get("headers"),
            body=arguments.get("body"),
            timeout=int(arguments.get("timeout", 10)),
        )

    def _http_debug(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.http_debug(
            url=str(arguments["url"]),
            debug_type=str(arguments.get("debug_type", "all")),
        )

    def _http_security(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.http_security(url=str(arguments["url"]))

    def _fetch_webpage_jina(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.fetch_webpage_jina(url=str(arguments["url"]))

    def _fetch_webpage_markdown(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.fetch_webpage_markdown(url=str(arguments["url"]))

    def _fetch_webpage_defuddle(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.fetch_webpage_defuddle(url=str(arguments["url"]))

    def _extract_web_content(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.extract_web_content(
            url=str(arguments["url"]),
            save_path=arguments.get("save_path"),
        )

    def _extract_and_summarize(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.extract_and_summarize(
            url=str(arguments["url"]),
            summary_type=str(arguments.get("summary_type", "brief")),
        )

    def _read_cached_page(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.read_cached_page(target_url=str(arguments["target_url"]))

    def _list_cached_pages(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.list_cached_pages()

    def _check_url_safety(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.check_url_safety(url=str(arguments["url"]))

    def _clear_cookies(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.clear_cookies(apply=self.apply_side_effects)

    def _api_test_request(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.api_test_request(
            url=str(arguments["url"]),
            method=str(arguments.get("method", "GET")),
            headers=arguments.get("headers"),
            body=arguments.get("body"),
        )

    def _api_test_health(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.api_test_health(url=str(arguments["url"]))

    def _api_test_json(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.api_test_json(
            url=str(arguments["url"]),
            method=str(arguments.get("method", "POST")),
            json_body=arguments.get("json_body"),
        )

    def _automation_navigate(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.automation_navigate(url=str(arguments["url"]))

    def _automation_click(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.automation_click(selector=str(arguments["selector"]))

    def _automation_input(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.automation_input(
            selector=str(arguments["selector"]),
            text=str(arguments["text"]),
        )

    def _automation_scroll(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.automation_scroll(
            direction=str(arguments.get("direction", "down")),
            amount=arguments.get("amount"),
        )

    def _automation_download(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.automation_download(
            url=str(arguments["url"]),
            save_path=arguments.get("save_path"),
        )

    def _automation_content(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.automation_content(
            extract_type=str(arguments.get("extract_type", "text")),
        )

    def _safety_check_url(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.safety_check_url(url=str(arguments["url"]))

    def _safety_check_file(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.safety_check_file(file_path=str(arguments["file_path"]))

    def _safety_scan_content(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.safety_scan_content(
            content=str(arguments["content"]),
            content_type=str(arguments.get("content_type", "text")),
        )

    def _security_scan_port(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.security_scan_port(
            target=str(arguments["target"]),
            ports=str(arguments.get("ports", "1-1000")),
        )

    def _security_scan_vulnerability(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.security_scan_vulnerability(target=str(arguments["target"]))

    def _security_scan_ssl(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.security_scan_ssl(target=str(arguments["target"]))

    def _security_audit(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.security_audit(
            target=str(arguments["target"]),
            audit_type=str(arguments.get("audit_type", "quick")),
        )

    def _dns_query(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.dns_query(
            domain=str(arguments["domain"]),
            record_type=str(arguments.get("record_type", "A")),
        )

    def _dns_debug(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.dns_debug(domain=str(arguments["domain"]))

    def _network_connectivity(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.network_connectivity(
            host=str(arguments["host"]),
            port=int(arguments.get("port", 80)),
            timeout=int(arguments.get("timeout", 5)),
        )

    def _proxy_test(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.proxy_test(
            proxy_url=str(arguments["proxy_url"]),
            test_url=str(arguments.get("test_url", "http://www.example.com")),
        )

    def _browser_use_open(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.browser_use_open(url=str(arguments["url"]))

    def _browser_use_state(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.browser_use_state()

    def _browser_use_click(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.browser_use_click(selector=str(arguments["selector"]))

    def _browser_use_input(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.browser_use_input(
            selector=str(arguments["selector"]),
            text=str(arguments["text"]),
        )

    def _browser_use_screenshot(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.browser_use_screenshot(save_path=arguments.get("save_path"))

    def _browser_use_cookies(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.browser_use_cookies(
            action=str(arguments.get("action", "get")),
            name=arguments.get("name"),
            value=arguments.get("value"),
        )

    def _fetch_web_page(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.fetch_web_page(
            target_url=str(arguments["target_url"]),
            extract_full_text=bool(arguments.get("extract_full_text", False)),
            download_attachments=bool(arguments.get("download_attachments", False)),
            include_internal_cookies=bool(arguments.get("include_internal_cookies", False)),
            apply=self.apply_side_effects,
        )

    def _list_downloaded_files(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.list_downloaded_files()

    def _get_page_metadata(self, arguments: dict[str, Any]) -> Any:
        return self.scenario.get_page_metadata(url=str(arguments["url"]))


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