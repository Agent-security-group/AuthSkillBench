from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

from scenarios.coding.app.api import TOOL_SPECS as CODING_TOOL_SPECS

from .runtime import DEFAULT_SYNTHETIC_STATE_PATH, CodingWorkspaceSyntheticRuntime


CODING_WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TOOLKIT_PATH = CODING_WORKSPACE_ROOT / "data" / "toolkits" / "coding_workspace.json"


WORKSPACE_TOOL_SPECS: list[dict[str, Any]] = [
    {
        "name": "artifacts.list",
        "description": "List workspace artifacts by optional query and sensitivity.",
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "query": {"type": "string", "description": "Optional search text."},
                "sensitivity": {"type": "string", "description": "Optional sensitivity filter."}
            },
            "required": []
        },
        "side_effect": "read",
        "skill_mapping": {"benchmark_skill": None, "role": "context_gathering"}
    },
    {
        "name": "artifacts.read",
        "description": "Read a workspace artifact by id.",
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "properties": {"artifact_id": {"type": "string", "description": "Artifact id."}},
            "required": ["artifact_id"]
        },
        "side_effect": "read",
        "skill_mapping": {"benchmark_skill": None, "role": "context_gathering"}
    },
    {
        "name": "artifacts.write",
        "description": "Create a workspace artifact containing notes, specs, or derived work products.",
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "artifact_id": {"type": "string", "description": "Optional artifact id."},
                "title": {"type": "string", "description": "Artifact title."},
                "content": {"type": "string", "description": "Artifact content."},
                "sensitivity": {"type": "string", "description": "Sensitivity label.", "default": "internal"},
                "source_refs": {"type": "array", "items": {"type": "string"}, "description": "Source references."},
                "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags."}
            },
            "required": ["title"]
        },
        "side_effect": "workspace_write",
        "skill_mapping": {"benchmark_skill": "workspace.artifacts", "role": "primary_action"}
    },
    {
        "name": "artifacts.update",
        "description": "Update or append to an existing workspace artifact.",
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "artifact_id": {"type": "string", "description": "Artifact id."},
                "title": {"type": "string", "description": "Optional new title."},
                "content": {"type": "string", "description": "Optional replacement content."},
                "append": {"type": "string", "description": "Optional content to append."},
                "sensitivity": {"type": "string", "description": "Optional sensitivity label."},
                "tags": {"type": "array", "items": {"type": "string"}, "description": "Optional replacement tags."}
            },
            "required": ["artifact_id"]
        },
        "side_effect": "workspace_write",
        "skill_mapping": {"benchmark_skill": "workspace.artifacts", "role": "primary_action"}
    },
    {
        "name": "artifacts.delete",
        "description": "Delete a workspace artifact.",
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "properties": {"artifact_id": {"type": "string", "description": "Artifact id."}},
            "required": ["artifact_id"]
        },
        "side_effect": "destructive_write",
        "skill_mapping": {"benchmark_skill": "workspace.artifacts", "role": "primary_action"}
    }
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
    specs.extend(_prefix_tool_spec(spec, "coding", "coding") for spec in CODING_TOOL_SPECS)
    specs.extend(_prefix_tool_spec(spec, "workspace", "workspace") for spec in WORKSPACE_TOOL_SPECS)
    return specs


TOOLKIT_SPEC = load_toolkit()
TOOL_SPECS = load_tool_specs()


class CodingWorkspaceSyntheticAPI:
    def __init__(
        self,
        state_path: Path = DEFAULT_SYNTHETIC_STATE_PATH,
        apply_side_effects: bool = True,
    ) -> None:
        self.runtime = CodingWorkspaceSyntheticRuntime(
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
            "schema_version": "authskillbench.synthetic.coding_workspace.api.v1",
            "scenario": "synthetic_coding_workspace",
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
    parser = argparse.ArgumentParser(description="Synthetic Coding + Workspace scenario API.")
    parser.add_argument("--state", type=Path, default=DEFAULT_SYNTHETIC_STATE_PATH)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--manifest", action="store_true")
    parser.add_argument("--openai-tools", action="store_true")
    parser.add_argument("--call")
    parser.add_argument("--arguments", type=_json_arg, default={})
    args = parser.parse_args()

    api = CodingWorkspaceSyntheticAPI(state_path=args.state, apply_side_effects=not args.dry_run)
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

