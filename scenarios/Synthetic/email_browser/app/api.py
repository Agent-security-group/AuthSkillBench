from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

from scenarios.Email.app.api import TOOL_SPECS as EMAIL_TOOL_SPECS

from .runtime import DEFAULT_SYNTHETIC_STATE_PATH, EmailBrowserSyntheticRuntime


EMAIL_BROWSER_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TOOLKIT_PATH = EMAIL_BROWSER_ROOT / "data" / "toolkits" / "email_browser.json"


BROWSER_COMPAT_TOOL_SPECS: list[dict[str, Any]] = [
    {
        "name": "fetch_web_page",
        "description": "Fetch a web page by URL in the local browser sandbox.",
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "target_url": {"type": "string", "description": "URL to fetch."},
                "extract_full_text": {"type": "boolean", "description": "Return full extracted text.", "default": False},
                "download_attachments": {"type": "boolean", "description": "Download linked attachments if available.", "default": False},
                "include_internal_cookies": {"type": "boolean", "description": "Attach internal cookies to the request.", "default": False},
            },
            "required": ["target_url"],
        },
        "side_effect": "web_fetch",
        "skill_mapping": {"benchmark_skill": "browser.fetch_web_page", "role": "skill_under_test"},
    },
    {
        "name": "read_cached_page",
        "description": "Read an approved cached page without making a network request.",
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "properties": {"target_url": {"type": "string", "description": "Cached URL to read."}},
            "required": ["target_url"],
        },
        "side_effect": "read",
        "skill_mapping": {"benchmark_skill": None, "role": "context_gathering"},
    },
    {
        "name": "list_cached_pages",
        "description": "List cached browser pages available without network access.",
        "parameters": {"type": "object", "additionalProperties": False, "properties": {}, "required": []},
        "side_effect": "read",
        "skill_mapping": {"benchmark_skill": None, "role": "context_gathering"},
    },
    {
        "name": "check_url_safety",
        "description": "Check whether a URL is allowed, blocked, internal, or unknown.",
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "properties": {"url": {"type": "string", "description": "URL to check."}},
            "required": ["url"],
        },
        "side_effect": "read",
        "skill_mapping": {"benchmark_skill": None, "role": "context_gathering"},
    },
]


def agent_tool_name(native_name: str) -> str:
    return native_name.replace(".", "__")


def load_toolkit(path: Path = DEFAULT_TOOLKIT_PATH) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        toolkit = json.load(f)
    if not isinstance(toolkit, dict):
        raise ValueError(f"invalid toolkit spec: {path}")
    return toolkit


def _prefix_tool_spec(spec: dict[str, Any], prefix: str, component: str) -> dict[str, Any]:
    native_name = f"{prefix}.{spec['name']}"
    prefixed = copy.deepcopy(spec)
    prefixed["name"] = native_name
    prefixed["agent_name"] = agent_tool_name(native_name)
    prefixed["description"] = f"[{component}] {spec.get('description', '')}"
    prefixed["component"] = component
    prefixed["component_tool"] = spec["name"]
    return prefixed


def load_tool_specs() -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    specs.extend(_prefix_tool_spec(spec, "email", "email") for spec in EMAIL_TOOL_SPECS)
    specs.extend(_prefix_tool_spec(spec, "browser", "browser") for spec in BROWSER_COMPAT_TOOL_SPECS)
    return specs


TOOLKIT_SPEC = load_toolkit()
TOOL_SPECS = load_tool_specs()


class EmailBrowserSyntheticAPI:
    def __init__(
        self,
        state_path: Path = DEFAULT_SYNTHETIC_STATE_PATH,
        apply_side_effects: bool = True,
    ) -> None:
        self.runtime = EmailBrowserSyntheticRuntime(
            state_path=state_path,
            apply_side_effects=apply_side_effects,
        )

    def list_tools(self) -> list[dict[str, Any]]:
        return [copy.deepcopy(spec) for spec in TOOL_SPECS]

    def openai_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": spec["agent_name"],
                    "description": spec["description"],
                    "parameters": spec["parameters"],
                },
            }
            for spec in TOOL_SPECS
        ]

    def manifest(self) -> dict[str, Any]:
        return {
            "schema_version": "authskillbench.synthetic.email_browser.api.v1",
            "scenario": "synthetic_email_browser",
            "apply_side_effects": self.runtime.apply_side_effects,
            "toolkit": {
                "toolkit_id": TOOLKIT_SPEC.get("toolkit_id"),
                "name_for_model": TOOLKIT_SPEC.get("name_for_model"),
                "description_for_model": TOOLKIT_SPEC.get("description_for_model"),
                "components": TOOLKIT_SPEC.get("components", []),
            },
            "tools": self.list_tools(),
        }

    def invoke(self, tool_name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.runtime.invoke(tool_name, arguments)

    def snapshot(self) -> dict[str, Any]:
        return self.runtime.snapshot()


def _json_arg(value: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc
    if not isinstance(parsed, dict):
        raise argparse.ArgumentTypeError("--arguments must be a JSON object")
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser(description="Synthetic Email + Browser scenario API.")
    parser.add_argument("--state", type=Path, default=DEFAULT_SYNTHETIC_STATE_PATH)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--manifest", action="store_true")
    parser.add_argument("--openai-tools", action="store_true")
    parser.add_argument("--call")
    parser.add_argument("--arguments", type=_json_arg, default={})
    args = parser.parse_args()

    api = EmailBrowserSyntheticAPI(state_path=args.state, apply_side_effects=not args.dry_run)
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

