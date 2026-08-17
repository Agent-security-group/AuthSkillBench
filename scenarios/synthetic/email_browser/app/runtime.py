from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Callable

from scenarios.email.app.api import DEFAULT_STATE_PATH as DEFAULT_EMAIL_STATE_PATH
from scenarios.email.app.api import EmailScenarioAPI
from scenarios.browser.app.api import DEFAULT_STATE_PATH as DEFAULT_BROWSER_STATE_PATH
from scenarios.browser.app.runtime import BrowserScenario


EMAIL_BROWSER_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SYNTHETIC_STATE_PATH = EMAIL_BROWSER_ROOT / "data" / "state.json"


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


class EmailBrowserSyntheticRuntime:
    """Facade that lets one agent task use Email and Browser tools together."""

    def __init__(
        self,
        *,
        state_path: Path = DEFAULT_SYNTHETIC_STATE_PATH,
        email_state_path: Path = DEFAULT_EMAIL_STATE_PATH,
        browser_state_path: Path = DEFAULT_BROWSER_STATE_PATH,
        apply_side_effects: bool = True,
    ) -> None:
        self.state = read_json(state_path)
        self.email = EmailScenarioAPI(state_path=email_state_path, apply_side_effects=apply_side_effects)
        self.browser = BrowserScenario.load(browser_state_path)
        self.apply_side_effects = apply_side_effects
        self.trace: list[dict[str, Any]] = []
        self._browser_handlers: dict[str, Callable[[dict[str, Any]], Any]] = {
            "fetch_web_page": self._browser_fetch_web_page,
            "read_cached_page": self._browser_read_cached_page,
            "list_cached_pages": self._browser_list_cached_pages,
            "check_url_safety": self._browser_check_url_safety,
        }

    def apply_threat_profile(self, profile: dict[str, Any] | None) -> None:
        if not profile:
            return
        overlays = profile.get("scenario_overlays") or {}
        if not isinstance(overlays, dict):
            raise ValueError("scenario_overlays must be an object")

        email_profile = overlays.get("email")
        if isinstance(email_profile, dict):
            self.email.scenario.apply_threat_profile(email_profile)

        browser_profile = overlays.get("browser")
        if isinstance(browser_profile, dict):
            self.browser.apply_threat_profile(browser_profile)

        synthetic_profile = overlays.get("synthetic")
        if isinstance(synthetic_profile, dict):
            self._apply_synthetic_overlay(synthetic_profile.get("state_overlay") or {})

    def invoke(self, tool_name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        native_name = tool_name.replace("__", ".")
        args = arguments or {}
        if native_name.startswith("email."):
            return self._invoke_component("email", native_name, native_name.removeprefix("email."), args)
        if native_name.startswith("browser."):
            return self._invoke_component("browser", native_name, native_name.removeprefix("browser."), args)
        return {
            "ok": False,
            "tool": native_name,
            "arguments": args,
            "error": f"unknown synthetic tool: {tool_name}",
        }

    def snapshot(self) -> dict[str, Any]:
        return {
            "schema_version": self.state.get("schema_version"),
            "scenario": "synthetic_email_browser",
            "email": self.email.snapshot(),
            "browser": self.browser.snapshot(),
            "trace": self.public_trace(),
        }

    def public_trace(self) -> list[dict[str, Any]]:
        return copy.deepcopy(self.trace)

    def _invoke_component(
        self,
        component: str,
        synthetic_tool: str,
        component_tool: str,
        args: dict[str, Any],
    ) -> dict[str, Any]:
        if component == "email":
            component_response = self.email.invoke(component_tool, args)
            ok = bool(component_response.get("ok"))
            result = component_response.get("result") if ok else None
            error = component_response.get("error")
        elif component == "browser":
            handler = self._browser_handlers.get(component_tool)
            if not handler:
                return {
                    "ok": False,
                    "tool": synthetic_tool,
                    "component": component,
                    "component_tool": component_tool,
                    "arguments": args,
                    "error": f"unknown browser compatibility tool: {component_tool}",
                }
            try:
                result = handler(args)
                ok = True
                error = None
            except Exception as exc:
                result = None
                ok = False
                error = str(exc)
        else:
            raise AssertionError(f"unsupported component: {component}")

        entry = {
            "component": component,
            "tool": synthetic_tool,
            "component_tool": component_tool,
            "arguments": copy.deepcopy(args),
            "ok": ok,
            "result_summary": self._summarize_result(result),
        }
        if error:
            entry["error"] = error
        self.trace.append(entry)

        response = {
            "ok": ok,
            "tool": synthetic_tool,
            "component": component,
            "component_tool": component_tool,
            "arguments": args,
            "result": result,
            "trace": self.public_trace(),
        }
        if error:
            response["error"] = error
        return response

    def _browser_fetch_web_page(self, arguments: dict[str, Any]) -> Any:
        return self.browser.fetch_web_page(
            target_url=str(arguments["target_url"]),
            extract_full_text=bool(arguments.get("extract_full_text", False)),
            download_attachments=bool(arguments.get("download_attachments", False)),
            include_internal_cookies=bool(arguments.get("include_internal_cookies", False)),
            apply=self.apply_side_effects,
        )

    def _browser_read_cached_page(self, arguments: dict[str, Any]) -> Any:
        return self.browser.read_cached_page(target_url=str(arguments["target_url"]))

    def _browser_list_cached_pages(self, arguments: dict[str, Any]) -> Any:
        return [
            {
                "id": page.get("id"),
                "url": page.get("url"),
                "title": page.get("title"),
                "cached_at": page.get("cached_at"),
                "source": page.get("source"),
                "trust": page.get("trust"),
                "sensitivity": page.get("sensitivity"),
                "content_summary": page.get("content_summary"),
                "labels": page.get("labels", []),
            }
            for page in self.browser.cached_pages()
        ]

    def _browser_check_url_safety(self, arguments: dict[str, Any]) -> Any:
        return self.browser.check_url_safety(url=str(arguments["url"]))

    def _apply_synthetic_overlay(self, overlay: dict[str, Any]) -> None:
        for op in overlay.get("ops", []):
            name = op.get("op")
            if name == "set_note":
                self.state.setdefault("notes", {})[str(op["key"])] = copy.deepcopy(op.get("value"))
            else:
                raise ValueError(f"unknown synthetic overlay operation: {name}")

    def _summarize_result(self, result: Any) -> Any:
        if isinstance(result, dict):
            summary_keys = [
                "id",
                "url",
                "domain",
                "status",
                "is_safe",
                "cached",
                "title",
                "sent_id",
                "draft_id",
                "export_id",
                "message_id",
                "count",
            ]
            summary = {key: result[key] for key in summary_keys if key in result}
            return summary or {"keys": sorted(result)[:12]}
        if isinstance(result, list):
            return {"count": len(result)}
        return result

