from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any


def normalize_email(value: str) -> str:
    return value.strip().strip("<>").lower()


def email_domain(value: str) -> str:
    email = normalize_email(value)
    return email.rsplit("@", 1)[1] if "@" in email else ""


def flatten_invocation_text(invocation: dict[str, Any]) -> str:
    parts: list[str] = [invocation.get("skill", ""), invocation.get("claimed_reason", "")]
    args = invocation.get("arguments", {})
    if isinstance(args, dict):
        for value in args.values():
            if isinstance(value, list):
                parts.extend(str(item) for item in value)
            elif value is not None:
                parts.append(str(value))
    return "\n".join(parts).lower()


class EmailSandbox:
    """Small deterministic email environment with Gmail-like tools.

    The sandbox is intentionally lightweight: it keeps state in JSON, exposes a
    few tool-like methods, and records trace entries so generated metadata is
    grounded in environment reads and candidate side effects.
    """

    def __init__(self, state: dict[str, Any]) -> None:
        self.state = copy.deepcopy(state)
        self.trace: list[dict[str, Any]] = []

    @classmethod
    def load(cls, path: Path) -> "EmailSandbox":
        with path.open("r", encoding="utf-8") as f:
            return cls(json.load(f))

    def reset_trace(self) -> None:
        self.trace = []

    def _record(self, tool: str, arguments: dict[str, Any], result: Any) -> Any:
        self.trace.append(
            {
                "tool": tool,
                "arguments": copy.deepcopy(arguments),
                "result": copy.deepcopy(result),
            }
        )
        return result

    def public_trace(self) -> list[dict[str, Any]]:
        compact: list[dict[str, Any]] = []
        for entry in self.trace:
            result = entry.get("result")
            if isinstance(result, dict):
                result_summary = {
                    key: result.get(key)
                    for key in ("id", "source", "from", "to", "subject", "ok", "message_id", "draft_id")
                    if key in result
                }
            elif isinstance(result, list):
                result_summary = {"count": len(result)}
            else:
                result_summary = result
            compact.append(
                {
                    "tool": entry["tool"],
                    "arguments": entry["arguments"],
                    "result_summary": result_summary,
                }
            )
        return compact

    def messages(self) -> list[dict[str, Any]]:
        return self.state.get("messages", [])

    def files(self) -> list[dict[str, Any]]:
        return self.state.get("files", [])

    def contacts(self) -> list[dict[str, Any]]:
        return self.state.get("contacts", [])

    def search_messages(self, query: str = "") -> list[dict[str, Any]]:
        query_lower = query.lower().strip()
        matches: list[dict[str, Any]] = []
        for message in self.messages():
            text = " ".join(
                [
                    message.get("from", ""),
                    message.get("subject", ""),
                    message.get("body", ""),
                    " ".join(message.get("labels", [])),
                ]
            ).lower()
            if not query_lower or query_lower in text:
                matches.append(
                    {
                        "id": message["id"],
                        "source": message["source"],
                        "from": message["from"],
                        "subject": message["subject"],
                    }
                )
        return self._record("email.search_messages", {"query": query}, matches)

    def read_message(self, message_id: str) -> dict[str, Any]:
        for message in self.messages():
            if message["id"] == message_id:
                visible = {
                    "id": message["id"],
                    "source": message["source"],
                    "from": message["from"],
                    "to": message.get("to", []),
                    "subject": message["subject"],
                    "body": message["body"],
                }
                return self._record("email.read_message", {"message_id": message_id}, visible)
        raise KeyError(f"unknown message id: {message_id}")

    def read_file(self, path: str) -> dict[str, Any]:
        for item in self.files():
            if item["path"] == path:
                visible = {
                    "path": item["path"],
                    "description": item.get("description", ""),
                    "content": item.get("content", ""),
                }
                return self._record("files.read", {"path": path}, visible)
        raise KeyError(f"unknown file path: {path}")

    def build_environment(self, observation_refs: list[str]) -> tuple[dict[str, str], list[dict[str, Any]]]:
        observations: list[dict[str, Any]] = []
        visible_blocks: list[str] = []
        sources: list[str] = []

        for ref in observation_refs:
            kind, _, ident = ref.partition(":")
            if kind == "message":
                visible = self.read_message(ident)
                hidden = self.message_by_id(ident)
                observations.append({"ref": ref, "visible": visible, "hidden": hidden})
                sources.append(visible["source"])
                visible_blocks.append(
                    "\n".join(
                        [
                            f"Source: {visible['source']}",
                            f"From: {visible['from']}",
                            f"Subject: {visible['subject']}",
                            f"Body: {visible['body']}",
                        ]
                    )
                )
            elif kind == "file":
                visible = self.read_file(ident)
                hidden = self.file_by_path(ident)
                observations.append({"ref": ref, "visible": visible, "hidden": hidden})
                sources.append("file")
                visible_blocks.append(f"File: {visible['path']}\nContent: {visible['content']}")
            else:
                raise ValueError(f"unknown observation ref kind: {ref}")

        source = "email_sandbox:" + "+".join(sorted(set(sources))) if sources else "email_sandbox"
        return {"source": source, "content": "\n\n".join(visible_blocks)}, observations

    def message_by_id(self, message_id: str) -> dict[str, Any]:
        for message in self.messages():
            if message["id"] == message_id:
                return message
        raise KeyError(f"unknown message id: {message_id}")

    def file_by_path(self, path: str) -> dict[str, Any]:
        for item in self.files():
            if item["path"] == path:
                return item
        raise KeyError(f"unknown file path: {path}")

    def contact_by_email(self, email: str) -> dict[str, Any] | None:
        normalized = normalize_email(email)
        for contact in self.contacts():
            if normalize_email(contact.get("email", "")) == normalized:
                return contact
        return None

    def classify_recipient(self, email: str) -> str:
        normalized = normalize_email(email)
        domain = email_domain(normalized)
        org_domains = set(self.state.get("account", {}).get("organization_domains", []))
        if domain in org_domains:
            return "internal"
        contact = self.contact_by_email(normalized)
        if contact and contact.get("approved") is True:
            return "approved_external"
        return "unapproved_external"

    def contacts_matching_name(self, text: str) -> list[dict[str, Any]]:
        text_lower = text.lower()
        matches: list[dict[str, Any]] = []
        for contact in self.contacts():
            name = contact.get("name", "").lower()
            first = name.split(" ", 1)[0] if name else ""
            if name and name in text_lower:
                matches.append(contact)
            elif first and re.search(rf"\b{re.escape(first)}\b", text_lower):
                matches.append(contact)
        return matches

    def sensitive_hits_for_text(self, text: str) -> list[str]:
        hits: list[str] = []
        for pattern in self.state.get("policies", {}).get("sensitive_patterns", []):
            if re.search(pattern, text, flags=re.IGNORECASE):
                hits.append(pattern)
        return sorted(set(hits))

    def sensitive_artifacts(self, invocation: dict[str, Any]) -> tuple[list[str], list[str]]:
        args = invocation.get("arguments", {})
        artifacts: list[str] = []
        terms: list[str] = []

        body = str(args.get("body", ""))
        terms.extend(self.sensitive_hits_for_text(body))

        for path in args.get("attachments", []) or []:
            try:
                item = self.file_by_path(path)
            except KeyError:
                artifacts.append(f"{path}:missing")
                continue
            content = item.get("content", "")
            file_terms = self.sensitive_hits_for_text(content)
            sensitivity = item.get("sensitivity", "public")
            if sensitivity != "public" or file_terms:
                artifacts.append(path)
                terms.extend(file_terms)
                if sensitivity != "public":
                    terms.append(f"file_sensitivity:{sensitivity}")

        return sorted(set(artifacts)), sorted(set(terms))

    def preview_state_diff(self, invocation: dict[str, Any]) -> dict[str, Any]:
        skill = invocation.get("skill")
        args = invocation.get("arguments", {})
        if skill == "gmail.users.messages.send":
            all_recipients = (args.get("to") or []) + (args.get("cc") or []) + (args.get("bcc") or [])
            return {
                "sent_messages_added": 1,
                "drafts_added": 0,
                "external_recipients": [
                    email
                    for email in all_recipients
                    if self.classify_recipient(email) != "internal"
                ],
            }
        if skill == "gmail.users.drafts.create":
            return {"sent_messages_added": 0, "drafts_added": 1}
        return {}

    def send_message(self, apply: bool = False, **arguments: Any) -> dict[str, Any]:
        message_id = f"sent_{len(self.state.setdefault('sent', [])) + 1:04d}"
        message = {
            "id": message_id,
            "from": self.state.get("account", {}).get("email", "me"),
            "to": arguments.get("to", []),
            "cc": arguments.get("cc", []),
            "bcc": arguments.get("bcc", []),
            "subject": arguments.get("subject", ""),
            "body": arguments.get("body", ""),
            "attachments": arguments.get("attachments", []),
        }
        if apply:
            self.state.setdefault("sent", []).append(message)
        return self._record(
            "gmail.users.messages.send",
            copy.deepcopy(arguments) | {"apply": apply},
            {"ok": True, "message_id": message_id, "applied": apply},
        )

    def create_draft(self, apply: bool = False, **arguments: Any) -> dict[str, Any]:
        draft_id = f"draft_{len(self.state.setdefault('drafts', [])) + 1:04d}"
        draft = {
            "id": draft_id,
            "from": self.state.get("account", {}).get("email", "me"),
            "to": arguments.get("to", []),
            "cc": arguments.get("cc", []),
            "subject": arguments.get("subject", ""),
            "body": arguments.get("body", ""),
            "attachments": arguments.get("attachments", []),
        }
        if apply:
            self.state.setdefault("drafts", []).append(draft)
        return self._record(
            "gmail.users.drafts.create",
            copy.deepcopy(arguments) | {"apply": apply},
            {"ok": True, "draft_id": draft_id, "applied": apply},
        )

    def run_invocation(self, invocation: dict[str, Any], apply: bool = False) -> dict[str, Any]:
        skill = invocation.get("skill")
        arguments = copy.deepcopy(invocation.get("arguments", {}))
        if skill == "gmail.users.messages.send":
            return self.send_message(apply=apply, **arguments)
        if skill == "gmail.users.drafts.create":
            return self.create_draft(apply=apply, **arguments)
        return self._record(skill or "unknown", arguments | {"apply": apply}, {"ok": False, "error": "unsupported skill"})
