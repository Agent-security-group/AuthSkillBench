from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Callable

from scenarios.coding.app.api import CodingAPI
from scenarios.coding.app.api import DEFAULT_STATE_PATH as DEFAULT_CODING_STATE_PATH


CODING_WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SYNTHETIC_STATE_PATH = CODING_WORKSPACE_ROOT / "data" / "state.json"


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


class CodingWorkspaceSyntheticRuntime:
    """Facade that combines a coding repo sandbox with a lightweight workspace."""

    def __init__(
        self,
        *,
        state_path: Path = DEFAULT_SYNTHETIC_STATE_PATH,
        coding_state_path: Path = DEFAULT_CODING_STATE_PATH,
        apply_side_effects: bool = True,
    ) -> None:
        self.state = read_json(state_path)
        self.coding = CodingAPI(sp=coding_state_path)
        self.apply_side_effects = apply_side_effects
        self.trace: list[dict[str, Any]] = []
        self._workspace_handlers: dict[str, Callable[[dict[str, Any]], Any]] = {
            "artifacts.list": self._workspace_list_artifacts,
            "artifacts.read": self._workspace_read_artifact,
            "artifacts.write": self._workspace_write_artifact,
            "artifacts.update": self._workspace_update_artifact,
            "artifacts.delete": self._workspace_delete_artifact,
        }

    def apply_threat_profile(self, profile: dict[str, Any] | None) -> None:
        if not profile:
            return
        overlays = profile.get("scenario_overlays") or {}
        if not isinstance(overlays, dict):
            raise ValueError("scenario_overlays must be an object")
        coding_profile = overlays.get("coding")
        if isinstance(coding_profile, dict):
            self.coding.repo.apply_threat_profile(coding_profile)
        workspace_profile = overlays.get("workspace")
        if isinstance(workspace_profile, dict):
            self._apply_workspace_overlay(workspace_profile.get("state_overlay") or {})

    def invoke(self, tool_name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        native_name = tool_name.replace("__", ".")
        args = arguments or {}
        if native_name.startswith("coding."):
            return self._invoke_coding(native_name, native_name.removeprefix("coding."), args)
        if native_name.startswith("workspace."):
            return self._invoke_workspace(native_name, native_name.removeprefix("workspace."), args)
        return {
            "ok": False,
            "tool": native_name,
            "arguments": args,
            "error": f"unknown synthetic tool: {tool_name}",
        }

    def snapshot(self) -> dict[str, Any]:
        repo = self.coding.repo.s
        return {
            "schema_version": self.state.get("schema_version"),
            "scenario": "synthetic_coding_workspace",
            "coding": {
                "current_branch": repo.get("current_branch"),
                "branch_count": len(repo.get("branches", {})),
                "pr_count": len(repo.get("pulls", {})),
                "issue_count": len(repo.get("issues", {})),
                "release_count": len(repo.get("releases", [])),
                "collaborator_count": len(repo.get("collaborators", [])),
            },
            "workspace": {
                "artifact_count": len(self.state.get("artifacts", [])),
                "artifacts": [
                    {
                        "artifact_id": item.get("artifact_id"),
                        "title": item.get("title"),
                        "sensitivity": item.get("sensitivity"),
                        "source_refs": item.get("source_refs", []),
                        "tags": item.get("tags", []),
                    }
                    for item in self.state.get("artifacts", [])
                ],
            },
            "trace": self.public_trace(),
        }

    def public_trace(self) -> list[dict[str, Any]]:
        return copy.deepcopy(self.trace)

    def _invoke_coding(self, synthetic_tool: str, component_tool: str, args: dict[str, Any]) -> dict[str, Any]:
        component_response = self.coding.invoke(component_tool, args)
        ok = bool(component_response.get("ok"))
        result = component_response.get("result") if ok else None
        error = component_response.get("error")
        self._record("coding", synthetic_tool, component_tool, args, ok, result, error)
        response = {
            "ok": ok,
            "tool": synthetic_tool,
            "component": "coding",
            "component_tool": component_tool,
            "arguments": args,
            "result": result,
            "trace": self.public_trace(),
        }
        if error:
            response["error"] = error
        return response

    def _invoke_workspace(self, synthetic_tool: str, component_tool: str, args: dict[str, Any]) -> dict[str, Any]:
        handler = self._workspace_handlers.get(component_tool)
        if not handler:
            return {
                "ok": False,
                "tool": synthetic_tool,
                "component": "workspace",
                "component_tool": component_tool,
                "arguments": args,
                "error": f"unknown workspace tool: {component_tool}",
            }
        try:
            result = handler(args)
            ok = True
            error = None
        except Exception as exc:
            result = None
            ok = False
            error = str(exc)
        self._record("workspace", synthetic_tool, component_tool, args, ok, result, error)
        response = {
            "ok": ok,
            "tool": synthetic_tool,
            "component": "workspace",
            "component_tool": component_tool,
            "arguments": args,
            "result": result,
            "trace": self.public_trace(),
        }
        if error:
            response["error"] = error
        return response

    def _workspace_list_artifacts(self, arguments: dict[str, Any]) -> list[dict[str, Any]]:
        query = str(arguments.get("query", "")).lower().strip()
        sensitivity = arguments.get("sensitivity")
        rows = []
        for item in self.state.get("artifacts", []):
            haystack = " ".join(
                [
                    str(item.get("artifact_id", "")),
                    str(item.get("title", "")),
                    str(item.get("content", "")),
                    " ".join(str(tag) for tag in item.get("tags", [])),
                ]
            ).lower()
            if query and query not in haystack:
                continue
            if sensitivity and item.get("sensitivity") != sensitivity:
                continue
            rows.append(
                {
                    "artifact_id": item.get("artifact_id"),
                    "title": item.get("title"),
                    "sensitivity": item.get("sensitivity"),
                    "source_refs": item.get("source_refs", []),
                    "tags": item.get("tags", []),
                    "content_preview": str(item.get("content", ""))[:240],
                }
            )
        return rows

    def _workspace_read_artifact(self, arguments: dict[str, Any]) -> dict[str, Any]:
        artifact = self._artifact_by_id(str(arguments["artifact_id"]))
        return copy.deepcopy(artifact)

    def _workspace_write_artifact(self, arguments: dict[str, Any]) -> dict[str, Any]:
        artifact_id = str(arguments.get("artifact_id") or self._next_artifact_id())
        if self._find_artifact(artifact_id) is not None:
            raise KeyError(f"artifact already exists: {artifact_id}")
        artifact = {
            "artifact_id": artifact_id,
            "title": str(arguments["title"]),
            "content": str(arguments.get("content", "")),
            "sensitivity": str(arguments.get("sensitivity", "internal")),
            "source_refs": list(arguments.get("source_refs", [])),
            "tags": list(arguments.get("tags", [])),
            "created_by": "agent",
        }
        if self.apply_side_effects:
            self.state.setdefault("artifacts", []).append(artifact)
        return {"artifact_id": artifact_id, "written": True, "applied": self.apply_side_effects}

    def _workspace_update_artifact(self, arguments: dict[str, Any]) -> dict[str, Any]:
        artifact = self._artifact_by_id(str(arguments["artifact_id"]))
        updated = copy.deepcopy(artifact)
        if "content" in arguments:
            updated["content"] = str(arguments["content"])
        if "append" in arguments:
            updated["content"] = str(updated.get("content", "")) + str(arguments["append"])
        if "title" in arguments:
            updated["title"] = str(arguments["title"])
        if "sensitivity" in arguments:
            updated["sensitivity"] = str(arguments["sensitivity"])
        if "tags" in arguments:
            updated["tags"] = list(arguments["tags"])
        if self.apply_side_effects:
            artifact.clear()
            artifact.update(updated)
        return {"artifact_id": updated["artifact_id"], "updated": True, "applied": self.apply_side_effects}

    def _workspace_delete_artifact(self, arguments: dict[str, Any]) -> dict[str, Any]:
        artifact_id = str(arguments["artifact_id"])
        artifact = self._artifact_by_id(artifact_id)
        if self.apply_side_effects:
            self.state["artifacts"] = [
                item for item in self.state.get("artifacts", []) if item.get("artifact_id") != artifact_id
            ]
        return {
            "artifact_id": artifact_id,
            "deleted": True,
            "applied": self.apply_side_effects,
            "sensitivity": artifact.get("sensitivity"),
        }

    def _apply_workspace_overlay(self, overlay: dict[str, Any]) -> None:
        applied_ids = self.state.setdefault("applied_threat_overlays", [])
        overlay_id = overlay.get("overlay_id")
        if overlay_id:
            applied_ids.append(overlay_id)
        for op in overlay.get("ops", []):
            name = op.get("op")
            if name == "upsert_artifact":
                artifact = copy.deepcopy(op["artifact"])
                existing = self._find_artifact(str(artifact["artifact_id"]))
                if existing is None:
                    self.state.setdefault("artifacts", []).append(artifact)
                else:
                    existing.update(artifact)
            elif name == "update_artifact":
                artifact = self._artifact_by_id(str(op["artifact_id"]))
                artifact.update(copy.deepcopy(op.get("set", {})))
            elif name == "remove_artifact":
                artifact_id = str(op["artifact_id"])
                self.state["artifacts"] = [
                    item for item in self.state.get("artifacts", []) if item.get("artifact_id") != artifact_id
                ]
            else:
                raise ValueError(f"unknown workspace overlay operation: {name}")

    def _find_artifact(self, artifact_id: str) -> dict[str, Any] | None:
        for item in self.state.setdefault("artifacts", []):
            if str(item.get("artifact_id")) == artifact_id:
                return item
        return None

    def _artifact_by_id(self, artifact_id: str) -> dict[str, Any]:
        artifact = self._find_artifact(artifact_id)
        if artifact is None:
            raise KeyError(f"artifact not found: {artifact_id}")
        return artifact

    def _next_artifact_id(self) -> str:
        next_ids = self.state.setdefault("next_ids", {})
        value = int(next_ids.get("artifact", 1))
        next_ids["artifact"] = value + 1
        return f"artifact_{value:03d}"

    def _record(
        self,
        component: str,
        synthetic_tool: str,
        component_tool: str,
        args: dict[str, Any],
        ok: bool,
        result: Any,
        error: str | None,
    ) -> None:
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

    def _summarize_result(self, result: Any) -> Any:
        if isinstance(result, dict):
            keys = [
                "artifact_id",
                "path",
                "commit",
                "branch",
                "id",
                "pr_id",
                "merged",
                "approved",
                "deleted",
                "version",
                "written",
                "updated",
            ]
            summary = {key: result[key] for key in keys if key in result}
            return summary or {"keys": sorted(result)[:12]}
        if isinstance(result, list):
            return {"count": len(result)}
        return result

