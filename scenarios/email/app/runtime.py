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


def _lower_values(values: list[Any]) -> list[str]:
    return [str(value).lower() for value in values]


def _message_date(message: dict[str, Any]) -> str:
    return str(message.get("date") or message.get("internal_date") or "")


def _upsert_by_key(items: list[dict[str, Any]], key: str, value: str, replacement: dict[str, Any]) -> None:
    for index, item in enumerate(items):
        if str(item.get(key)) == value:
            merged = copy.deepcopy(item)
            merged.update(copy.deepcopy(replacement))
            items[index] = merged
            return
    items.append(copy.deepcopy(replacement))


class EmailScenario:
    """Small deterministic email scenario with Gmail-like tools.

    The scenario is intentionally lightweight: it keeps state in JSON, exposes a
    few tool-like methods, and records trace entries so generated metadata is
    grounded in threat-context reads and candidate side effects.
    """

    def __init__(self, state: dict[str, Any]) -> None:
        self.state = copy.deepcopy(state)
        self.trace: list[dict[str, Any]] = []

    @classmethod
    def load(cls, path: Path) -> "EmailScenario":
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

    def drafts(self) -> list[dict[str, Any]]:
        return self.state.get("drafts", [])

    def apply_threat_profile(self, profile: dict[str, Any] | None) -> None:
        """Apply profile-specific state changes without recording agent-visible trace."""

        if not profile:
            return
        overlay = profile.get("state_overlay") or {}
        if not isinstance(overlay, dict):
            raise ValueError("threat state_overlay must be an object")
        self.apply_overlay(overlay)

    def _select_messages(self, selector: dict[str, Any]) -> list[dict[str, Any]]:
        if not selector:
            return []
        if "ids" in selector:
            ids = {str(item) for item in selector.get("ids", [])}
            return [message for message in self.messages() if message.get("id") in ids]
        if "id" in selector:
            message_id = str(selector["id"])
            return [message for message in self.messages() if message.get("id") == message_id]
        query = str(selector.get("query", ""))
        selected = [message for message in self.messages() if self._message_matches_query(message, query)]
        thread_id = selector.get("thread_id")
        if thread_id:
            selected = [message for message in selected if message.get("thread_id") == thread_id]
        source = selector.get("source")
        if source:
            selected = [message for message in selected if message.get("source") == source]
        trust = selector.get("trust")
        if trust:
            selected = [message for message in selected if message.get("trust") == trust]
        return selected

    def apply_overlay(self, overlay: dict[str, Any]) -> None:
        ops = overlay.get("ops", [])
        if not isinstance(ops, list):
            raise ValueError("state_overlay.ops must be a list")
        applied_ids = self.state.setdefault("applied_threat_overlays", [])
        overlay_id = overlay.get("overlay_id")
        if overlay_id:
            applied_ids.append(overlay_id)

        for op in ops:
            if not isinstance(op, dict):
                raise ValueError("overlay operation must be an object")
            name = op.get("op")
            if name == "upsert_message":
                message = op.get("message")
                if not isinstance(message, dict) or not isinstance(message.get("id"), str):
                    raise ValueError("upsert_message requires message.id")
                _upsert_by_key(self.state.setdefault("messages", []), "id", message["id"], message)
            elif name == "upsert_messages":
                messages = op.get("messages", [])
                if not isinstance(messages, list):
                    raise ValueError("upsert_messages requires a messages list")
                for message in messages:
                    if not isinstance(message, dict) or not isinstance(message.get("id"), str):
                        raise ValueError("upsert_messages requires every message.id")
                    _upsert_by_key(self.state.setdefault("messages", []), "id", message["id"], message)
            elif name == "update_message":
                selector = op.get("match", {})
                patch = op.get("set", {})
                if not isinstance(selector, dict) or not isinstance(patch, dict):
                    raise ValueError("update_message requires match and set objects")
                for message in self._select_messages(selector):
                    message.update(copy.deepcopy(patch))
            elif name == "remove_message":
                message_id = str(op["id"])
                self.state["messages"] = [item for item in self.messages() if item.get("id") != message_id]
            elif name == "remove_messages":
                selector = op.get("match", {})
                if not isinstance(selector, dict):
                    raise ValueError("remove_messages requires a match object")
                remove_ids = {message["id"] for message in self._select_messages(selector)}
                self.state["messages"] = [item for item in self.messages() if item.get("id") not in remove_ids]
            elif name == "add_message_labels":
                selector = op.get("match", {})
                labels = op.get("labels", [])
                if not isinstance(selector, dict) or not isinstance(labels, list):
                    raise ValueError("add_message_labels requires match object and labels list")
                for message in self._select_messages(selector):
                    existing = {label.lower() for label in message.setdefault("labels", [])}
                    for label in labels:
                        if str(label).lower() not in existing:
                            message["labels"].append(str(label))
            elif name == "remove_message_labels":
                selector = op.get("match", {})
                labels = {str(label).lower() for label in op.get("labels", [])}
                if not isinstance(selector, dict):
                    raise ValueError("remove_message_labels requires a match object")
                for message in self._select_messages(selector):
                    message["labels"] = [label for label in message.get("labels", []) if label.lower() not in labels]
            elif name == "add_message_attachment":
                selector = op.get("match", {})
                attachment = op.get("attachment")
                if not isinstance(selector, dict) or not isinstance(attachment, str):
                    raise ValueError("add_message_attachment requires match object and attachment string")
                for message in self._select_messages(selector):
                    attachments = message.setdefault("attachments", [])
                    if attachment not in attachments:
                        attachments.append(attachment)
            elif name == "replace_message_recipient":
                selector = op.get("match", {})
                field = str(op.get("field", "to"))
                old = normalize_email(str(op.get("old", "")))
                new = normalize_email(str(op.get("new", "")))
                if field not in {"to", "cc", "bcc"} or not isinstance(selector, dict):
                    raise ValueError("replace_message_recipient requires match object and to/cc/bcc field")
                for message in self._select_messages(selector):
                    values = message.setdefault(field, [])
                    message[field] = [new if normalize_email(value) == old else value for value in values]
            elif name == "upsert_contact":
                contact = op.get("contact")
                if not isinstance(contact, dict) or not isinstance(contact.get("email"), str):
                    raise ValueError("upsert_contact requires contact.email")
                _upsert_by_key(
                    self.state.setdefault("contacts", []),
                    "email",
                    normalize_email(contact["email"]),
                    contact | {"email": normalize_email(contact["email"])},
                )
            elif name == "update_contact":
                match = op.get("match", {})
                patch = op.get("set", {})
                if not isinstance(match, dict) or not isinstance(patch, dict):
                    raise ValueError("update_contact requires match and set objects")
                email = normalize_email(str(match.get("email", "")))
                updated = False
                for contact in self.contacts():
                    if normalize_email(contact.get("email", "")) == email:
                        contact.update(copy.deepcopy(patch))
                        updated = True
                if not updated:
                    raise KeyError(f"update_contact could not find {email}")
            elif name == "remove_contact":
                email = normalize_email(str(op["email"]))
                self.state["contacts"] = [item for item in self.contacts() if normalize_email(item.get("email", "")) != email]
            elif name == "add_contact_alias":
                email = normalize_email(str(op["email"]))
                alias = str(op["alias"])
                for contact in self.contacts():
                    if normalize_email(contact.get("email", "")) == email:
                        aliases = contact.setdefault("aliases", [])
                        if alias not in aliases:
                            aliases.append(alias)
                        break
                else:
                    raise KeyError(f"add_contact_alias could not find {email}")
            elif name == "upsert_file":
                item = op.get("file")
                if not isinstance(item, dict) or not isinstance(item.get("path"), str):
                    raise ValueError("upsert_file requires file.path")
                _upsert_by_key(self.state.setdefault("files", []), "path", item["path"], item)
            elif name == "update_file":
                path = str(op["path"])
                patch = op.get("set", {})
                if not isinstance(patch, dict):
                    raise ValueError("update_file requires set object")
                item = self.file_by_path(path)
                item.update(copy.deepcopy(patch))
            elif name == "append_file_content":
                path = str(op["path"])
                content = str(op.get("content", ""))
                item = self.file_by_path(path)
                item["content"] = str(item.get("content", "")) + content
            elif name == "remove_file":
                path = str(op["path"])
                self.state["files"] = [item for item in self.files() if item.get("path") != path]
            elif name == "set_current_time":
                self.state["current_time"] = str(op["value"])
            elif name == "set_policy":
                key = str(op["key"])
                self.state.setdefault("policies", {})[key] = copy.deepcopy(op.get("value"))
            elif name == "append_policy_list":
                key = str(op["key"])
                values = op.get("values", [])
                if not isinstance(values, list):
                    raise ValueError("append_policy_list requires values list")
                target = self.state.setdefault("policies", {}).setdefault(key, [])
                if not isinstance(target, list):
                    raise ValueError(f"policy {key} is not a list")
                for value in values:
                    if value not in target:
                        target.append(value)
            else:
                raise ValueError(f"unknown overlay operation: {name}")

    def _message_matches_query(self, message: dict[str, Any], query: str) -> bool:
        query = query.strip()
        if not query:
            return True
        filters: list[tuple[str, str]] = []
        terms: list[str] = []
        for raw_token in query.split():
            token = raw_token.strip()
            if ":" in token:
                key, value = token.split(":", 1)
                filters.append((key.lower(), value.lower()))
            else:
                terms.append(token.lower())

        labels = _lower_values(message.get("labels", []))
        attachments = message.get("attachments", []) or []
        text = " ".join(
            [
                message.get("from", ""),
                " ".join(message.get("to", [])),
                " ".join(message.get("cc", [])),
                " ".join(message.get("bcc", [])),
                message.get("subject", ""),
                message.get("body", ""),
                " ".join(message.get("labels", [])),
                message.get("thread_id", ""),
            ]
        ).lower()

        for key, value in filters:
            if key == "from" and value not in message.get("from", "").lower():
                return False
            if key == "to" and value not in " ".join(_lower_values(message.get("to", []))):
                return False
            if key == "cc" and value not in " ".join(_lower_values(message.get("cc", []))):
                return False
            if key == "subject" and value not in message.get("subject", "").lower():
                return False
            if key == "label" and value not in labels:
                return False
            if key == "thread" and value != message.get("thread_id", "").lower():
                return False
            if key == "in" and value not in labels and value != str(message.get("mailbox", "")).lower():
                return False
            if key == "has" and value == "attachment" and not attachments:
                return False
            if key == "after" and _message_date(message) <= value:
                return False
            if key == "before" and _message_date(message) >= value:
                return False
        return all(term in text for term in terms)

    def search_messages(self, query: str = "") -> list[dict[str, Any]]:
        matches: list[dict[str, Any]] = []
        for message in self.messages():
            if self._message_matches_query(message, query):
                matches.append(
                    {
                        "id": message["id"],
                        "thread_id": message.get("thread_id"),
                        "source": message["source"],
                        "from": message["from"],
                        "to": message.get("to", []),
                        "subject": message["subject"],
                        "date": message.get("date"),
                        "labels": message.get("labels", []),
                        "has_attachments": bool(message.get("attachments")),
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
                    "cc": message.get("cc", []),
                    "bcc": message.get("bcc", []),
                    "subject": message["subject"],
                    "body": message["body"],
                    "date": message.get("date"),
                    "thread_id": message.get("thread_id"),
                    "labels": message.get("labels", []),
                    "attachments": message.get("attachments", []),
                }
                return self._record("email.read_message", {"message_id": message_id}, visible)
        raise KeyError(f"unknown message id: {message_id}")

    def read_thread(self, thread_id: str) -> dict[str, Any]:
        messages = [message for message in self.messages() if message.get("thread_id") == thread_id]
        if not messages:
            raise KeyError(f"unknown thread id: {thread_id}")
        visible = {
            "thread_id": thread_id,
            "message_count": len(messages),
            "messages": [
                {
                    "id": message["id"],
                    "source": message["source"],
                    "from": message["from"],
                    "to": message.get("to", []),
                    "cc": message.get("cc", []),
                    "subject": message["subject"],
                    "body": message["body"],
                    "date": message.get("date"),
                    "labels": message.get("labels", []),
                    "attachments": message.get("attachments", []),
                }
                for message in sorted(messages, key=_message_date)
            ],
        }
        return self._record("email.read_thread", {"thread_id": thread_id}, visible)

    def list_threads(self, query: str = "") -> list[dict[str, Any]]:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for message in self.messages():
            if self._message_matches_query(message, query):
                grouped.setdefault(message.get("thread_id") or message["id"], []).append(message)
        threads: list[dict[str, Any]] = []
        for thread_id, messages in grouped.items():
            ordered = sorted(messages, key=_message_date)
            participants = sorted(
                set([item.get("from", "") for item in messages] + [addr for item in messages for addr in item.get("to", [])])
            )
            threads.append(
                {
                    "thread_id": thread_id,
                    "message_count": len(messages),
                    "latest_date": _message_date(ordered[-1]),
                    "subject": ordered[-1].get("subject", ""),
                    "participants": participants,
                    "labels": sorted(set(label for item in messages for label in item.get("labels", []))),
                }
            )
        return self._record("email.list_threads", {"query": query}, sorted(threads, key=lambda item: item["latest_date"], reverse=True))

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

    def list_files(self, include_sensitive: bool = False) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for item in self.files():
            if not include_sensitive and item.get("sensitivity") not in (None, "public"):
                continue
            result.append(
                {
                    "path": item["path"],
                    "description": item.get("description", ""),
                    "sensitivity": item.get("sensitivity", "unknown"),
                    "size": len(str(item.get("content", ""))),
                }
            )
        return self._record("files.list", {"include_sensitive": include_sensitive}, result)

    def file_metadata(self, path: str) -> dict[str, Any]:
        item = self.file_by_path(path)
        result = {
            "path": item["path"],
            "description": item.get("description", ""),
            "sensitivity": item.get("sensitivity", "unknown"),
            "size": len(str(item.get("content", ""))),
        }
        return self._record("files.metadata", {"path": path}, result)

    def build_threat(self, observation_refs: list[str]) -> tuple[dict[str, str], list[dict[str, Any]]]:
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

        source = "email_scenario:" + "+".join(sorted(set(sources))) if sources else "email_scenario"
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

    def draft_by_id(self, draft_id: str) -> dict[str, Any]:
        for draft in self.drafts():
            if draft["id"] == draft_id:
                return draft
        raise KeyError(f"unknown draft id: {draft_id}")

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

    def search_contacts(self, query: str = "", relationship: str | None = None, approved: bool | None = None) -> list[dict[str, Any]]:
        query_lower = query.lower().strip()
        matches: list[dict[str, Any]] = []
        for contact in self.contacts():
            haystack = " ".join(
                [
                    contact.get("name", ""),
                    contact.get("email", ""),
                    contact.get("relationship", ""),
                    " ".join(contact.get("approved_for", [])),
                ]
            ).lower()
            if query_lower and query_lower not in haystack:
                continue
            if relationship and contact.get("relationship") != relationship:
                continue
            if approved is not None and contact.get("approved") is not approved:
                continue
            matches.append(
                {
                    "name": contact.get("name"),
                    "email": contact.get("email"),
                    "relationship": contact.get("relationship"),
                    "approved": contact.get("approved"),
                    "approved_for": contact.get("approved_for", []),
                    "verification_status": contact.get("verification_status", "unknown"),
                    "last_verified_at": contact.get("last_verified_at"),
                }
            )
        return self._record(
            "contacts.search",
            {"query": query, "relationship": relationship, "approved": approved},
            matches,
        )

    def verify_contact_current(self, email: str, purpose: str | None = None) -> dict[str, Any]:
        contact = self.contact_by_email(email)
        if not contact:
            result = {"email": normalize_email(email), "ok": False, "verification_status": "missing"}
            return self._record("contacts.verify_current", {"email": email, "purpose": purpose}, result)
        approved_for = contact.get("approved_for", [])
        purpose_ok = purpose is None or purpose in approved_for
        status = contact.get("verification_status", "unknown")
        result = {
            "email": contact.get("email"),
            "name": contact.get("name"),
            "ok": contact.get("approved") is True and purpose_ok and status == "current",
            "approved": contact.get("approved"),
            "purpose_ok": purpose_ok,
            "approved_for": approved_for,
            "verification_status": status,
            "last_verified_at": contact.get("last_verified_at"),
        }
        return self._record("contacts.verify_current", {"email": email, "purpose": purpose}, result)

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
        if skill == "gmail.users.drafts.update":
            return {"drafts_updated": 1, "draft_id": args.get("draft_id") or args.get("id")}
        if skill == "gmail.users.drafts.send":
            return {"drafts_sent": 1, "sent_messages_added": 1, "draft_id": args.get("draft_id") or args.get("id")}
        if skill == "gmail.users.messages.forward":
            return {
                "sent_messages_added": 1,
                "forwarded_message_id": args.get("message_id"),
                "external_recipients": [
                    email
                    for email in (args.get("to") or []) + (args.get("cc") or []) + (args.get("bcc") or [])
                    if self.classify_recipient(email) != "internal"
                ],
            }
        if skill == "email.export_messages":
            return {"messages_exported": len(args.get("message_ids", []) or []), "destination": args.get("destination")}
        if skill == "gmail.users.messages.trash":
            return {"messages_trashed": 1, "message_ids": [args.get("id") or args.get("message_id")]}
        if skill == "gmail.users.messages.delete":
            return {"messages_deleted": 1, "message_ids": [args.get("id") or args.get("message_id")]}
        if skill == "gmail.users.messages.batchModify":
            return {
                "messages_modified": len(args.get("ids", []) or []),
                "message_ids": args.get("ids", []) or [],
                "add_labels": args.get("addLabelIds", []) or args.get("add_labels", []) or [],
                "remove_labels": args.get("removeLabelIds", []) or args.get("remove_labels", []) or [],
            }
        return {}

    def send_message(self, apply: bool = False, **arguments: Any) -> dict[str, Any]:
        message_id = f"sent_{len(self.state.setdefault('sent', [])) + 1:04d}"
        message = {
            "id": message_id,
            "thread_id": arguments.get("thread_id", message_id),
            "date": self.state.get("current_time"),
            "source": "sent_mail",
            "trust": "trusted",
            "from": self.state.get("account", {}).get("email", "me"),
            "to": arguments.get("to", []),
            "cc": arguments.get("cc", []),
            "bcc": arguments.get("bcc", []),
            "subject": arguments.get("subject", ""),
            "body": arguments.get("body", ""),
            "attachments": arguments.get("attachments", []),
            "labels": ["sent"],
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
            "thread_id": arguments.get("thread_id", draft_id),
            "date": self.state.get("current_time"),
            "from": self.state.get("account", {}).get("email", "me"),
            "to": arguments.get("to", []),
            "cc": arguments.get("cc", []),
            "bcc": arguments.get("bcc", []),
            "subject": arguments.get("subject", ""),
            "body": arguments.get("body", ""),
            "attachments": arguments.get("attachments", []),
            "labels": ["draft"],
        }
        if apply:
            self.state.setdefault("drafts", []).append(draft)
        return self._record(
            "gmail.users.drafts.create",
            copy.deepcopy(arguments) | {"apply": apply},
            {"ok": True, "draft_id": draft_id, "applied": apply},
        )

    def update_draft(self, draft_id: str, apply: bool = False, **arguments: Any) -> dict[str, Any]:
        draft = self.draft_by_id(draft_id)
        allowed_fields = {"to", "cc", "bcc", "subject", "body", "attachments", "thread_id"}
        patch = {key: copy.deepcopy(value) for key, value in arguments.items() if key in allowed_fields}
        if apply:
            draft.update(patch)
        return self._record(
            "gmail.users.drafts.update",
            {"draft_id": draft_id, **patch, "apply": apply},
            {"ok": True, "draft_id": draft_id, "applied": apply},
        )

    def send_draft(self, draft_id: str, apply: bool = False, **arguments: Any) -> dict[str, Any]:
        draft = self.draft_by_id(draft_id)
        send_args = {
            "userId": arguments.get("userId", "me"),
            "to": draft.get("to", []),
            "cc": draft.get("cc", []),
            "bcc": draft.get("bcc", []),
            "subject": draft.get("subject", ""),
            "body": draft.get("body", ""),
            "attachments": draft.get("attachments", []),
            "thread_id": draft.get("thread_id"),
        }
        send_result = self.send_message(apply=apply, **send_args)
        if apply:
            self.state["drafts"] = [item for item in self.drafts() if item.get("id") != draft_id]
        return self._record(
            "gmail.users.drafts.send",
            {"draft_id": draft_id, **copy.deepcopy(arguments), "apply": apply},
            {"ok": True, "draft_id": draft_id, "message_id": send_result.get("message_id"), "applied": apply},
        )

    def forward_message(
        self,
        message_id: str,
        to: list[str],
        apply: bool = False,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
        body: str = "",
        attachments: list[str] | None = None,
        **arguments: Any,
    ) -> dict[str, Any]:
        original = self.message_by_id(message_id)
        forwarded_body = "\n\n".join(
            part
            for part in [
                body,
                "----- Forwarded message -----",
                f"From: {original.get('from', '')}",
                f"Subject: {original.get('subject', '')}",
                original.get("body", ""),
            ]
            if part
        )
        send_args = {
            "userId": arguments.get("userId", "me"),
            "to": to,
            "cc": cc or [],
            "bcc": bcc or [],
            "subject": arguments.get("subject") or f"Fwd: {original.get('subject', '')}",
            "body": forwarded_body,
            "attachments": attachments if attachments is not None else original.get("attachments", []),
            "thread_id": arguments.get("thread_id", f"fwd_{message_id}"),
        }
        send_result = self.send_message(apply=apply, **send_args)
        return self._record(
            "gmail.users.messages.forward",
            {"message_id": message_id, **send_args, "apply": apply},
            {"ok": True, "message_id": send_result.get("message_id"), "forwarded_message_id": message_id, "applied": apply},
        )

    def export_messages(self, message_ids: list[str], destination: str, include_attachments: bool = False, apply: bool = False) -> dict[str, Any]:
        exported = [self.message_by_id(message_id) for message_id in message_ids]
        export_record = {
            "id": f"export_{len(self.state.setdefault('exports', [])) + 1:04d}",
            "destination": destination,
            "message_ids": message_ids,
            "include_attachments": include_attachments,
            "message_count": len(exported),
        }
        if apply:
            self.state.setdefault("exports", []).append(export_record)
        return self._record(
            "email.export_messages",
            {"message_ids": message_ids, "destination": destination, "include_attachments": include_attachments, "apply": apply},
            {"ok": True, **export_record, "applied": apply},
        )

    def trash_message(self, message_id: str, apply: bool = False, **arguments: Any) -> dict[str, Any]:
        message = self.message_by_id(message_id)
        if apply:
            labels = message.setdefault("labels", [])
            if "trash" not in _lower_values(labels):
                labels.append("trash")
            if "inbox" in _lower_values(labels):
                message["labels"] = [label for label in labels if label.lower() != "inbox"]
            message["mailbox"] = "trash"
        return self._record(
            "gmail.users.messages.trash",
            {"message_id": message_id, **copy.deepcopy(arguments), "apply": apply},
            {"ok": True, "message_id": message_id, "applied": apply},
        )

    def delete_message(self, message_id: str, apply: bool = False, **arguments: Any) -> dict[str, Any]:
        self.message_by_id(message_id)
        if apply:
            self.state["messages"] = [message for message in self.messages() if message.get("id") != message_id]
        return self._record(
            "gmail.users.messages.delete",
            {"message_id": message_id, **copy.deepcopy(arguments), "apply": apply},
            {"ok": True, "message_id": message_id, "applied": apply},
        )

    def batch_modify_messages(
        self,
        ids: list[str],
        add_labels: list[str] | None = None,
        remove_labels: list[str] | None = None,
        apply: bool = False,
        **arguments: Any,
    ) -> dict[str, Any]:
        add_labels = add_labels or []
        remove_labels = remove_labels or []
        messages = [self.message_by_id(message_id) for message_id in ids]
        if apply:
            remove_set = {label.lower() for label in remove_labels}
            for message in messages:
                labels = [label for label in message.get("labels", []) if label.lower() not in remove_set]
                existing = {label.lower() for label in labels}
                for label in add_labels:
                    if label.lower() not in existing:
                        labels.append(label)
                message["labels"] = labels
        return self._record(
            "gmail.users.messages.batchModify",
            {
                "ids": ids,
                "add_labels": add_labels,
                "remove_labels": remove_labels,
                **copy.deepcopy(arguments),
                "apply": apply,
            },
            {"ok": True, "message_ids": ids, "applied": apply},
        )

    def run_invocation(self, invocation: dict[str, Any], apply: bool = False) -> dict[str, Any]:
        skill = invocation.get("skill")
        arguments = copy.deepcopy(invocation.get("arguments", {}))
        if skill == "gmail.users.messages.send":
            return self.send_message(apply=apply, **arguments)
        if skill == "gmail.users.drafts.create":
            return self.create_draft(apply=apply, **arguments)
        if skill == "gmail.users.drafts.update":
            draft_id = str(arguments.pop("draft_id", arguments.pop("id", "")))
            return self.update_draft(draft_id=draft_id, apply=apply, **arguments)
        if skill == "gmail.users.drafts.send":
            draft_id = str(arguments.pop("draft_id", arguments.pop("id", "")))
            return self.send_draft(draft_id=draft_id, apply=apply, **arguments)
        if skill == "gmail.users.messages.forward":
            message_id = str(arguments.pop("message_id", arguments.pop("id", "")))
            to = arguments.pop("to", [])
            return self.forward_message(message_id=message_id, to=to, apply=apply, **arguments)
        if skill == "email.export_messages":
            message_ids = arguments.pop("message_ids", [])
            destination = str(arguments.pop("destination", ""))
            include_attachments = bool(arguments.pop("include_attachments", False))
            return self.export_messages(message_ids=message_ids, destination=destination, include_attachments=include_attachments, apply=apply)
        if skill == "gmail.users.messages.trash":
            message_id = str(arguments.pop("message_id", arguments.pop("id", "")))
            return self.trash_message(message_id=message_id, apply=apply, **arguments)
        if skill == "gmail.users.messages.delete":
            message_id = str(arguments.pop("message_id", arguments.pop("id", "")))
            return self.delete_message(message_id=message_id, apply=apply, **arguments)
        if skill == "gmail.users.messages.batchModify":
            ids = arguments.pop("ids", [])
            add_labels = arguments.pop("add_labels", arguments.pop("addLabelIds", []))
            remove_labels = arguments.pop("remove_labels", arguments.pop("removeLabelIds", []))
            return self.batch_modify_messages(ids=ids, add_labels=add_labels, remove_labels=remove_labels, apply=apply, **arguments)
        return self._record(skill or "unknown", arguments | {"apply": apply}, {"ok": False, "error": "unsupported skill"})
