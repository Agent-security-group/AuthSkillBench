#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from ..app.api import DEFAULT_STATE_PATH, EmailSandboxAPI
except ImportError:  # pragma: no cover - supports direct script execution.
    sys.path.append(str(Path(__file__).resolve().parents[3]))
    from sandboxes.email.app.api import DEFAULT_STATE_PATH, EmailSandboxAPI


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a small agent-style interaction against the email sandbox API.")
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE_PATH)
    parser.add_argument("--output", type=Path, help="Write the demo transcript to a JSON file.")
    args = parser.parse_args()

    api = EmailSandboxAPI(state_path=args.state, apply_side_effects=True)
    transcript = {
        "manifest": api.manifest(),
        "steps": [
            api.invoke("email.search_messages", {"query": "onboarding"}),
            api.invoke("email.read_message", {"message_id": "msg_onboarding_copy"}),
            api.invoke(
                "gmail.users.drafts.create",
                {
                    "userId": "me",
                    "to": ["pat@example.com"],
                    "subject": "Onboarding schedule",
                    "body": "Hi Pat, your onboarding sessions are Monday 10:00 and Tuesday 14:00.",
                },
            ),
        ],
        "snapshot": api.snapshot(),
    }

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", encoding="utf-8") as f:
            json.dump(transcript, f, indent=2, sort_keys=False)
            f.write("\n")
        print(f"Wrote email sandbox API demo transcript to {args.output}")
    else:
        print(json.dumps(transcript, indent=2, sort_keys=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
