#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .api import DEFAULT_STATE_PATH, EmailSandboxAPI
from .benchmark import (
    generate_case,
    generate_cases,
    list_cases,
    list_contrast_groups,
    list_environment_groups,
    list_environment_profiles,
    list_task_groups,
    load_case,
    load_environment_profile,
)


def _json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict[str, Any] | list[Any]) -> None:
    body = json.dumps(payload, indent=2, sort_keys=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _read_json(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length", "0"))
    if length == 0:
        return {}
    raw = handler.rfile.read(length)
    if not raw:
        return {}
    data = json.loads(raw.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("request body must be a JSON object")
    return data


def make_handler(state_path: Path, apply_side_effects: bool) -> type[BaseHTTPRequestHandler]:
    class EmailSandboxHandler(BaseHTTPRequestHandler):
        api = EmailSandboxAPI(state_path=state_path, apply_side_effects=apply_side_effects)

        def log_message(self, format: str, *args: Any) -> None:
            return

        def do_GET(self) -> None:
            path = urlparse(self.path).path
            try:
                if path == "/health":
                    _json_response(self, 200, {"ok": True, "service": "email_sandbox"})
                elif path == "/agent/manifest":
                    _json_response(self, 200, self.api.manifest())
                elif path == "/agent/tools":
                    _json_response(self, 200, self.api.list_tools())
                elif path == "/agent/toolkit":
                    _json_response(self, 200, self.api.manifest()["toolkit"])
                elif path == "/agent/openai-tools":
                    _json_response(self, 200, self.api.openai_tools())
                elif path == "/agent/snapshot":
                    _json_response(self, 200, self.api.snapshot())
                elif path == "/benchmark/cases":
                    _json_response(self, 200, {"cases": list_cases()})
                elif path.startswith("/benchmark/cases/"):
                    case_id = path.rsplit("/", 1)[-1]
                    _json_response(self, 200, load_case(case_id))
                elif path == "/benchmark/contrast-groups":
                    _json_response(self, 200, {"contrast_groups": list_contrast_groups()})
                elif path == "/benchmark/task-groups":
                    _json_response(self, 200, {"task_groups": list_task_groups()})
                elif path == "/benchmark/environment-groups":
                    _json_response(self, 200, {"environment_groups": list_environment_groups()})
                elif path == "/benchmark/environments":
                    _json_response(self, 200, {"environments": list_environment_profiles()})
                elif path.startswith("/benchmark/environments/"):
                    profile_id = path.rsplit("/", 1)[-1]
                    _json_response(self, 200, load_environment_profile(profile_id))
                else:
                    _json_response(self, 404, {"ok": False, "error": f"unknown route: {path}"})
            except Exception as exc:
                _json_response(self, 500, {"ok": False, "error": str(exc)})

        def do_POST(self) -> None:
            path = urlparse(self.path).path
            try:
                payload = _read_json(self)
                if path == "/agent/invoke":
                    tool = payload.get("tool") or payload.get("tool_name")
                    if not isinstance(tool, str):
                        _json_response(self, 400, {"ok": False, "error": "tool is required"})
                        return
                    arguments = payload.get("arguments") or {}
                    if not isinstance(arguments, dict):
                        _json_response(self, 400, {"ok": False, "error": "arguments must be an object"})
                        return
                    _json_response(self, 200, self.api.invoke(tool, arguments))
                elif path == "/agent/reset":
                    self.__class__.api = EmailSandboxAPI(state_path=state_path, apply_side_effects=apply_side_effects)
                    _json_response(self, 200, {"ok": True, "snapshot": self.api.snapshot()})
                elif path == "/benchmark/build-case":
                    case_id = payload.get("case_id")
                    if not isinstance(case_id, str):
                        _json_response(self, 400, {"ok": False, "error": "case_id is required"})
                        return
                    _json_response(self, 200, generate_case(load_case(case_id), state_path=state_path))
                elif path == "/benchmark/generate-cases":
                    selected = payload.get("case_ids") or []
                    if not isinstance(selected, list) or not all(isinstance(item, str) for item in selected):
                        _json_response(self, 400, {"ok": False, "error": "case_ids must be a list of strings"})
                        return
                    _json_response(self, 200, {"cases": generate_cases(selected=selected, state_path=state_path)})
                else:
                    _json_response(self, 404, {"ok": False, "error": f"unknown route: {path}"})
            except json.JSONDecodeError as exc:
                _json_response(self, 400, {"ok": False, "error": f"invalid JSON: {exc}"})
            except Exception as exc:
                _json_response(self, 500, {"ok": False, "error": str(exc)})

    return EmailSandboxHandler


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the AuthSkillBench email sandbox as an HTTP API.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE_PATH)
    parser.add_argument("--dry-run", action="store_true", help="Preview side effects instead of mutating runtime state.")
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), make_handler(args.state, apply_side_effects=not args.dry_run))
    print(f"Email sandbox API listening on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
