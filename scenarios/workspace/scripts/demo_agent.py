#!/usr/bin/env python3
"""Simple API demo for the workspace scenario without an LLM."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scenarios.workspace.app.api import DEFAULT_STATE_PATH, WorkspaceScenarioAPI


def main() -> int:
    parser = argparse.ArgumentParser(description="Workspace scenario API demo.")
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE_PATH)
    parser.add_argument("--apply", action="store_true", help="Apply side effects.")
    parser.add_argument("--output", type=Path, default=None, help="Output transcript path.")
    args = parser.parse_args()

    api = WorkspaceScenarioAPI(state_path=args.state, apply_side_effects=args.apply)
    transcript: list[dict[str, Any]] = []

    def log(step: str, payload: Any) -> None:
        transcript.append({"step": step, "payload": payload})
        label = f"\n--- {step} ---"
        print(label)
        print(json.dumps(payload, indent=2, sort_keys=False, ensure_ascii=False))

    # 1. Manifest
    log("manifest", api.manifest())

    # 2. List tools
    log("tools_count", len(api.list_tools()))

    # 3. List root folder
    log("list_root_folder", api.invoke("files.list_folder", {"folder_id": "f_root", "include_permissions": True}))

    # 4. Search for proposal
    log("search_proposal", api.invoke("files.search", {"query": "proposal"}))

    # 5. Read proposal metadata
    log("proposal_metadata", api.invoke("files.metadata", {"file_id": "file_proposal"}))

    # 6. Read version history
    log("proposal_versions", api.invoke("files.version_history", {"file_id": "file_proposal"}))

    # 7. Try to read file without permission (budget file — view only, no export)
    log("budget_metadata", api.invoke("files.metadata", {"file_id": "file_budget_confidential"}))

    # 8. Try to export without permission
    log("budget_export_attempt", api.invoke("files.export", {"file_id": "file_budget_confidential", "destination": "external_vendor_system"}))

    # 9. Edit proposal
    log("edit_proposal", api.invoke("files.edit", {
        "file_id": "file_proposal",
        "content": "# Q3 Proposal\n\n## Overview\nThis project aims to expand market reach in the APAC region.\n\n## Budget\nTotal requested: $55,000 (updated)\n\n## Timeline\n- Phase 1: August 2026\n- Phase 2: September 2026\n\n## Status\nDraft — pending CFO review."
    }))

    # 10. Search members
    log("search_members", api.invoke("members.search", {"query": "alice"}))

    # 11. Snapshot
    log("snapshot", api.snapshot())

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", encoding="utf-8") as f:
            json.dump(transcript, f, indent=2, sort_keys=False, ensure_ascii=False)
        print(f"\nTranscript saved to {args.output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
