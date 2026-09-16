from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any


def normalize_email(value: str) -> str:
    return value.strip().strip("<>").lower()


def _upsert_by_key(items: list[dict[str, Any]], key: str, value: str, replacement: dict[str, Any]) -> None:
    for index, item in enumerate(items):
        if str(item.get(key)) == value:
            merged = copy.deepcopy(item)
            merged.update(copy.deepcopy(replacement))
            items[index] = merged
            return
    items.append(copy.deepcopy(replacement))


# Permission constants
PERM_VIEW = "view"
PERM_COPY = "copy"
PERM_EDIT = "edit"
PERM_SHARE = "share"
PERM_DELETE = "delete"
PERM_EXPORT = "export"
PERM_OWNER = "owner"
_ALL_PERMS = [PERM_VIEW, PERM_COPY, PERM_EDIT, PERM_SHARE, PERM_DELETE, PERM_EXPORT, PERM_OWNER]


def owner_permissions() -> list[str]:
    return list(_ALL_PERMS)


def _has_permission(user_email: str, perm: str, file_perms: dict[str, list[str]]) -> bool:
    """Check if a user has a specific permission on a file."""
    user_perms = file_perms.get(user_email, [])
    if perm in user_perms:
        return True
    return PERM_OWNER in user_perms


def _filter_visible(user_email: str, files: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter files to only those visible to the user, and strip hidden fields."""
    visible: list[dict[str, Any]] = []
    for item in files:
        perms = item.get("permissions", {})
        if not _has_permission(user_email, PERM_VIEW, perms):
            continue
        visible_item = {
            "id": item["id"],
            "name": item.get("name"),
            "folder_id": item.get("folder_id"),
            "owner": item.get("owner"),
            "version": item.get("version", 1),
            "approved_version": item.get("approved_version"),
            "tags": item.get("tags", []),
            "created_at": item.get("created_at"),
            "updated_at": item.get("updated_at"),
            "size": len(str(item.get("content", ""))),
            "permissions": _visible_permissions(user_email, perms),
        }
        if _has_permission(user_email, PERM_EXPORT, perms):
            visible_item["export_formats"] = item.get("export_formats", ["md"])
        visible.append(visible_item)
    return visible


def _visible_permissions(user_email: str, perms: dict[str, list[str]]) -> dict[str, list[str]]:
    """Return a redacted permissions view — only show what the current user has."""
    return {user_email: perms.get(user_email, [])}


def _check_permission_or_raise(user_email: str, perm: str, file_perms: dict[str, Any], action_desc: str) -> None:
    if not _has_permission(user_email, perm, file_perms):
        raise PermissionError(f"User {user_email} does not have '{perm}' permission to {action_desc}")


class WorkspaceScenario:
    """Deterministic workspace scenario with Google-Drive-like file/folder management.

    The scenario models a collaborative file space where files have fine-grained
    permissions (view, copy, edit, share, delete, export) and ownership.
    """

    def __init__(self, state: dict[str, Any]) -> None:
        self.state = copy.deepcopy(state)
        self.trace: list[dict[str, Any]] = []

    @classmethod
    def load(cls, path: Path) -> WorkspaceScenario:
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
                    for key in (
                        "id", "ok", "name", "folder_id", "owner", "version",
                        "file_count", "folder_count", "member_count",
                        "action", "target", "status",
                    )
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

    # ── Helpers ──────────────────────────────────────────────

    def account_email(self) -> str:
        return str(self.state.get("account", {}).get("email", "me"))

    def current_user_id(self) -> str:
        return self.account_email()

    def files(self) -> list[dict[str, Any]]:
        return self.state.get("files", [])

    def folders(self) -> list[dict[str, Any]]:
        return self.state.get("folders", [])

    def members(self) -> list[dict[str, Any]]:
        return self.state.get("members", [])

    def file_by_id(self, file_id: str) -> dict[str, Any]:
        for item in self.files():
            if item.get("id") == file_id:
                return item
        raise KeyError(f"unknown file id: {file_id}")

    def folder_by_id(self, folder_id: str) -> dict[str, Any]:
        for item in self.folders():
            if item.get("id") == folder_id:
                return item
        raise KeyError(f"unknown folder id: {folder_id}")

    def member_by_email(self, email: str) -> dict[str, Any] | None:
        normalized = normalize_email(email)
        for member in self.members():
            if normalize_email(member.get("email", "")) == normalized:
                return member
        return None

    def sensitive_hits_for_text(self, text: str) -> list[str]:
        hits: list[str] = []
        for pattern in self.state.get("policies", {}).get("sensitive_patterns", []):
            if re.search(pattern, text, flags=re.IGNORECASE):
                hits.append(pattern)
        return sorted(set(hits))

    def _member_visible(self, member: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": member.get("id"),
            "name": member.get("name"),
            "email": member.get("email"),
            "role": member.get("role", "viewer"),
        }

    # ── Threat Overlay ───────────────────────────────────────

    def apply_threat_profile(self, profile: dict[str, Any] | None) -> None:
        if not profile:
            return
        overlay = profile.get("state_overlay") or {}
        if not isinstance(overlay, dict):
            raise ValueError("threat state_overlay must be an object")
        self.apply_overlay(overlay)

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
            if name == "upsert_file":
                item = op.get("file")
                if not isinstance(item, dict) or not isinstance(item.get("id"), str):
                    raise ValueError("upsert_file requires file.id")
                _upsert_by_key(self.state.setdefault("files", []), "id", item["id"], item)
            elif name == "update_file":
                file_id = str(op.get("id", ""))
                patch = op.get("set", {})
                if not isinstance(patch, dict):
                    raise ValueError("update_file requires set object")
                item = self.file_by_id(file_id)
                item.update(copy.deepcopy(patch))
            elif name == "update_file_permissions":
                file_id = str(op.get("id", ""))
                user_email = normalize_email(str(op.get("user_email", "")))
                perms = op.get("permissions", [])
                if not isinstance(perms, list):
                    raise ValueError("update_file_permissions requires permissions list")
                item = self.file_by_id(file_id)
                file_perms = item.setdefault("permissions", {})
                file_perms[user_email] = list(perms)
            elif name == "remove_file":
                file_id = str(op.get("id", ""))
                self.state["files"] = [item for item in self.files() if item.get("id") != file_id]
            elif name == "move_file":
                file_id = str(op.get("id", ""))
                target_folder_id = str(op.get("target_folder_id", ""))
                item = self.file_by_id(file_id)
                item["folder_id"] = target_folder_id
            elif name == "upsert_folder":
                folder = op.get("folder")
                if not isinstance(folder, dict) or not isinstance(folder.get("id"), str):
                    raise ValueError("upsert_folder requires folder.id")
                _upsert_by_key(self.state.setdefault("folders", []), "id", folder["id"], folder)
            elif name == "remove_folder":
                folder_id = str(op.get("id", ""))
                self.state["folders"] = [item for item in self.folders() if item.get("id") != folder_id]
            elif name == "upsert_member":
                member = op.get("member")
                if not isinstance(member, dict) or not isinstance(member.get("email"), str):
                    raise ValueError("upsert_member requires member.email")
                _upsert_by_key(
                    self.state.setdefault("members", []),
                    "email",
                    normalize_email(member["email"]),
                    member,
                )
            elif name == "remove_member":
                email = normalize_email(str(op.get("email", "")))
                self.state["members"] = [
                    m for m in self.members() if normalize_email(m.get("email", "")) != email
                ]
            elif name == "append_file_content":
                file_id = str(op.get("id", ""))
                content = str(op.get("content", ""))
                item = self.file_by_id(file_id)
                item["content"] = str(item.get("content", "")) + content
            elif name == "set_approved_version":
                file_id = str(op.get("id", ""))
                version = int(op.get("version", 1))
                item = self.file_by_id(file_id)
                item["approved_version"] = version
            elif name == "set_current_time":
                self.state["current_time"] = str(op.get("value", ""))
            elif name == "set_policy":
                key = str(op.get("key", ""))
                self.state.setdefault("policies", {})[key] = copy.deepcopy(op.get("value"))
            elif name == "append_policy_list":
                key = str(op.get("key", ""))
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

    # ── Agent-Facing Tools ───────────────────────────────────

    def search_files(self, query: str = "", folder_id: str | None = None, tags: list[str] | None = None) -> list[dict[str, Any]]:
        """Search workspace files visible to the current user."""
        user = self.current_user_id()
        query_lower = query.lower().strip()
        tag_set = set(tag.lower() for tag in (tags or []))
        matches: list[dict[str, Any]] = []
        visible_files = _filter_visible(user, self.files())
        for item in visible_files:
            if folder_id and item.get("folder_id") != folder_id:
                continue
            if tag_set and not tag_set.intersection(t.lower() for t in item.get("tags", [])):
                continue
            if query_lower:
                haystack = " ".join([
                    item.get("name", ""),
                    item.get("id", ""),
                    item.get("owner", ""),
                    " ".join(item.get("tags", [])),
                ]).lower()
                if query_lower not in haystack:
                    continue
            matches.append(item)
        return self._record("files.search", {"query": query, "folder_id": folder_id, "tags": tags}, matches)

    def read_file(self, file_id: str) -> dict[str, Any]:
        """Read file content. Requires view permission."""
        user = self.current_user_id()
        item = self.file_by_id(file_id)
        perms = item.get("permissions", {})
        _check_permission_or_raise(user, PERM_VIEW, perms, f"read file {file_id}")
        visible = {
            "id": item["id"],
            "name": item.get("name"),
            "folder_id": item.get("folder_id"),
            "owner": item.get("owner"),
            "version": item.get("version", 1),
            "approved_version": item.get("approved_version"),
            "content": item.get("content", ""),
            "tags": item.get("tags", []),
            "created_at": item.get("created_at"),
            "updated_at": item.get("updated_at"),
        }
        if _has_permission(user, PERM_EXPORT, perms):
            visible["export_formats"] = item.get("export_formats", ["md"])
        return self._record("files.read", {"file_id": file_id}, visible)

    def file_metadata(self, file_id: str) -> dict[str, Any]:
        """Read file metadata without content. Requires view permission."""
        user = self.current_user_id()
        item = self.file_by_id(file_id)
        perms = item.get("permissions", {})
        _check_permission_or_raise(user, PERM_VIEW, perms, f"view metadata of file {file_id}")
        result = {
            "id": item["id"],
            "name": item.get("name"),
            "folder_id": item.get("folder_id"),
            "owner": item.get("owner"),
            "version": item.get("version", 1),
            "approved_version": item.get("approved_version"),
            "size": len(str(item.get("content", ""))),
            "tags": item.get("tags", []),
            "created_at": item.get("created_at"),
            "updated_at": item.get("updated_at"),
            "your_permissions": perms.get(user, []),
        }
        return self._record("files.metadata", {"file_id": file_id}, result)

    def list_folder(self, folder_id: str, include_permissions: bool = False) -> dict[str, Any]:
        """List files and sub-folders in a folder. Returns visible items only."""
        user = self.current_user_id()
        self.folder_by_id(folder_id)  # validate folder exists
        items: list[dict[str, Any]] = []
        for f in self.folders():
            if f.get("parent_id") == folder_id:
                items.append({
                    "type": "folder",
                    "id": f["id"],
                    "name": f.get("name"),
                    "owner": f.get("owner"),
                })
        for file in _filter_visible(user, self.files()):
            if file.get("folder_id") == folder_id:
                entry: dict[str, Any] = {
                    "type": "file",
                    "id": file["id"],
                    "name": file.get("name"),
                    "owner": file.get("owner"),
                    "version": file.get("version", 1),
                    "tags": file.get("tags", []),
                    "updated_at": file.get("updated_at"),
                }
                if include_permissions:
                    entry["your_permissions"] = file.get("permissions", {}).get(user, [])
                items.append(entry)
        result = {
            "folder_id": folder_id,
            "folder_name": self.folder_by_id(folder_id).get("name"),
            "item_count": len(items),
            "items": items,
        }
        return self._record("files.list_folder", {"folder_id": folder_id, "include_permissions": include_permissions}, result)

    def version_history(self, file_id: str) -> dict[str, Any]:
        """View file version history. Requires view permission."""
        user = self.current_user_id()
        item = self.file_by_id(file_id)
        perms = item.get("permissions", {})
        _check_permission_or_raise(user, PERM_VIEW, perms, f"view version history of file {file_id}")
        history = item.get("version_history", [])
        result = {
            "file_id": file_id,
            "file_name": item.get("name"),
            "current_version": item.get("version", 1),
            "approved_version": item.get("approved_version"),
            "versions": list(history) if history else [{"version": item.get("version", 1), "description": "current"}],
        }
        return self._record("files.version_history", {"file_id": file_id}, result)

    def create_file(self, name: str, content: str, folder_id: str, tags: list[str] | None = None, apply: bool = False) -> dict[str, Any]:
        """Create a new file. Always allowed for authenticated users in writable folders."""
        self.folder_by_id(folder_id)  # validate folder exists
        user = self.current_user_id()
        file_id = f"file_{len(self.files()) + 1:04d}"
        file_entry: dict[str, Any] = {
            "id": file_id,
            "name": name,
            "folder_id": folder_id,
            "owner": user,
            "version": 1,
            "approved_version": 1,
            "content": content,
            "tags": tags or [],
            "permissions": {
                user: owner_permissions(),
            },
            "created_at": self.state.get("current_time", "2026-06-01T09:00:00+08:00"),
            "updated_at": self.state.get("current_time", "2026-06-01T09:00:00+08:00"),
        }
        if apply:
            self.state.setdefault("files", []).append(file_entry)
        result = {
            "ok": True,
            "file_id": file_id,
            "applied": apply,
            "version": 1,
        }
        return self._record("files.create", {"name": name, "folder_id": folder_id, "tags": tags, "apply": apply}, result)

    def edit_file(self, file_id: str, content: str | None = None, name: str | None = None, apply: bool = False) -> dict[str, Any]:
        """Edit file content or name. Requires edit permission."""
        user = self.current_user_id()
        item = self.file_by_id(file_id)
        perms = item.get("permissions", {})
        _check_permission_or_raise(user, PERM_EDIT, perms, f"edit file {file_id}")
        if apply:
            new_version = item.get("version", 1) + 1
            item["version"] = new_version
            if content is not None:
                item["content"] = content
            if name is not None:
                item["name"] = name
            item["updated_at"] = self.state.get("current_time", "2026-06-01T09:00:00+08:00")
            vh = item.setdefault("version_history", [])
            vh.append({"version": new_version, "timestamp": item["updated_at"]})
        result = {
            "ok": True,
            "file_id": file_id,
            "applied": apply,
            "new_version": item.get("version", 2) if apply else item.get("version", 1),
            "sensitive_hits": self.sensitive_hits_for_text(content or ""),
        }
        return self._record("files.edit", {"file_id": file_id, "content_preview": (content or "")[:50], "apply": apply}, result)

    def copy_file(self, file_id: str, target_folder_id: str, new_name: str | None = None, apply: bool = False) -> dict[str, Any]:
        """Copy a file to another folder. Requires copy permission on source file."""
        user = self.current_user_id()
        item = self.file_by_id(file_id)
        perms = item.get("permissions", {})
        _check_permission_or_raise(user, PERM_COPY, perms, f"copy file {file_id}")
        self.folder_by_id(target_folder_id)  # validate target
        new_file_id = f"file_{len(self.files()) + 1:04d}"
        name = new_name or f"Copy of {item.get('name', 'untitled')}"
        if apply:
            copy_entry = copy.deepcopy(item)
            copy_entry["id"] = new_file_id
            copy_entry["name"] = name
            copy_entry["folder_id"] = target_folder_id
            copy_entry["owner"] = user
            copy_entry["version"] = 1
            copy_entry["approved_version"] = 1
            copy_entry["permissions"] = {user: owner_permissions()}
            copy_entry["created_at"] = self.state.get("current_time", "2026-06-01T09:00:00+08:00")
            copy_entry["updated_at"] = self.state.get("current_time", "2026-06-01T09:00:00+08:00")
            copy_entry.pop("version_history", None)
            self.state.setdefault("files", []).append(copy_entry)
        result = {
            "ok": True,
            "source_file_id": file_id,
            "target_file_id": new_file_id,
            "target_folder_id": target_folder_id,
            "new_name": name,
            "applied": apply,
        }
        return self._record("files.copy", {"file_id": file_id, "target_folder_id": target_folder_id, "new_name": name, "apply": apply}, result)

    def move_file(self, file_id: str, target_folder_id: str, apply: bool = False) -> dict[str, Any]:
        """Move a file to another folder. Requires edit permission on the file."""
        user = self.current_user_id()
        item = self.file_by_id(file_id)
        perms = item.get("permissions", {})
        _check_permission_or_raise(user, PERM_EDIT, perms, f"move file {file_id}")
        self.folder_by_id(target_folder_id)  # validate target
        if apply:
            item["folder_id"] = target_folder_id
            item["updated_at"] = self.state.get("current_time", "2026-06-01T09:00:00+08:00")
        result = {
            "ok": True,
            "file_id": file_id,
            "target_folder_id": target_folder_id,
            "applied": apply,
        }
        return self._record("files.move", {"file_id": file_id, "target_folder_id": target_folder_id, "apply": apply}, result)

    def delete_file(self, file_id: str, permanent: bool = False, apply: bool = False) -> dict[str, Any]:
        """Delete a file. Requires delete permission. Owner can always delete."""
        user = self.current_user_id()
        item = self.file_by_id(file_id)
        perms = item.get("permissions", {})
        _check_permission_or_raise(user, PERM_DELETE, perms, f"delete file {file_id}")
        if apply:
            self.state["files"] = [f for f in self.files() if f.get("id") != file_id]
        result = {
            "ok": True,
            "file_id": file_id,
            "permanent": permanent,
            "applied": apply,
        }
        return self._record("files.delete", {"file_id": file_id, "permanent": permanent, "apply": apply}, result)

    def archive_file(self, file_id: str, apply: bool = False) -> dict[str, Any]:
        """Archive a file (remove from active view). Requires edit permission."""
        user = self.current_user_id()
        item = self.file_by_id(file_id)
        perms = item.get("permissions", {})
        _check_permission_or_raise(user, PERM_EDIT, perms, f"archive file {file_id}")
        if apply:
            tags = item.setdefault("tags", [])
            if "archived" not in tags:
                tags.append("archived")
            item["updated_at"] = self.state.get("current_time", "2026-06-01T09:00:00+08:00")
        result = {
            "ok": True,
            "file_id": file_id,
            "applied": apply,
        }
        return self._record("files.archive", {"file_id": file_id, "apply": apply}, result)

    def export_file(self, file_id: str, destination: str, format: str = "md", apply: bool = False) -> dict[str, Any]:
        """Export a file to an external destination. Requires export permission."""
        user = self.current_user_id()
        item = self.file_by_id(file_id)
        perms = item.get("permissions", {})
        _check_permission_or_raise(user, PERM_EXPORT, perms, f"export file {file_id}")
        content = item.get("content", "")
        sensitive_hits = self.sensitive_hits_for_text(content)
        approved_destinations = self.state.get("policies", {}).get("approved_export_destinations", [])
        destination_ok = not approved_destinations or destination in approved_destinations
        if apply:
            exports = self.state.setdefault("exports", [])
            exports.append({
                "file_id": file_id,
                "destination": destination,
                "format": format,
                "exported_at": self.state.get("current_time"),
            })
        result = {
            "ok": True,
            "file_id": file_id,
            "destination": destination,
            "format": format,
            "applied": apply,
            "destination_approved": destination_ok,
            "sensitive_hits": sensitive_hits,
            "size": len(content),
        }
        return self._record("files.export", {"file_id": file_id, "destination": destination, "format": format, "apply": apply}, result)

    def share_file(self, file_id: str, user_email: str, permissions: list[str], apply: bool = False) -> dict[str, Any]:
        """Change file permissions for a user. Requires share permission on the file."""
        user = self.current_user_id()
        normalized_target = normalize_email(user_email)
        item = self.file_by_id(file_id)
        perms = item.get("permissions", {})
        _check_permission_or_raise(user, PERM_SHARE, perms, f"share file {file_id}")
        # Validate permissions
        for p in permissions:
            if p not in _ALL_PERMS and p != PERM_OWNER:
                raise ValueError(f"unknown permission: {p}")
        if apply:
            file_perms = item.setdefault("permissions", {})
            file_perms[normalized_target] = list(permissions)
            item["updated_at"] = self.state.get("current_time", "2026-06-01T09:00:00+08:00")
        result = {
            "ok": True,
            "file_id": file_id,
            "user_email": normalized_target,
            "permissions": permissions,
            "applied": apply,
        }
        return self._record("files.share", {"file_id": file_id, "user_email": user_email, "permissions": permissions, "apply": apply}, result)

    def create_archive(self, file_ids: list[str], archive_name: str, apply: bool = False) -> dict[str, Any]:
        """Create an archive (zip) of selected files. Requires view + export permission on each file."""
        user = self.current_user_id()
        archived: list[str] = []
        blocked: list[str] = []
        sensitive_hits: list[str] = []
        for fid in file_ids:
            try:
                item = self.file_by_id(fid)
                perms = item.get("permissions", {})
                if not _has_permission(user, PERM_VIEW, perms) or not _has_permission(user, PERM_EXPORT, perms):
                    blocked.append(fid)
                    continue
                archived.append(fid)
                content = item.get("content", "")
                sensitive_hits.extend(self.sensitive_hits_for_text(content))
            except KeyError:
                blocked.append(fid)
        if apply:
            archives = self.state.setdefault("archives", [])
            archives.append({
                "name": archive_name,
                "file_ids": archived,
                "created_at": self.state.get("current_time"),
            })
        result = {
            "ok": True,
            "archive_name": archive_name,
            "file_count": len(archived),
            "blocked_count": len(blocked),
            "blocked_file_ids": blocked if blocked else None,
            "sensitive_hits": sorted(set(sensitive_hits)),
            "applied": apply,
        }
        return self._record("files.create_archive", {"file_ids": file_ids, "archive_name": archive_name, "apply": apply}, result)

    def create_folder(self, name: str, parent_id: str | None = None, apply: bool = False) -> dict[str, Any]:
        """Create a new folder."""
        user = self.current_user_id()
        if parent_id:
            self.folder_by_id(parent_id)  # validate parent
        folder_id = f"f_{len(self.folders()) + 1:04d}"
        folder_entry: dict[str, Any] = {
            "id": folder_id,
            "name": name,
            "parent_id": parent_id,
            "owner": user,
        }
        if apply:
            self.state.setdefault("folders", []).append(folder_entry)
        result = {
            "ok": True,
            "folder_id": folder_id,
            "name": name,
            "applied": apply,
        }
        return self._record("files.create_folder", {"name": name, "parent_id": parent_id, "apply": apply}, result)

    def search_members(self, query: str = "") -> list[dict[str, Any]]:
        """Search workspace members."""
        query_lower = query.lower().strip()
        matches: list[dict[str, Any]] = []
        for member in self.members():
            haystack = " ".join([
                member.get("name", ""),
                member.get("email", ""),
                member.get("role", ""),
            ]).lower()
            if query_lower and query_lower not in haystack:
                continue
            matches.append(self._member_visible(member))
        return self._record("members.search", {"query": query}, matches)

    def get_member_permissions(self, email: str) -> dict[str, Any]:
        """Get what permissions a member has across the workspace (summary)."""
        normalized = normalize_email(email)
        member = self.member_by_email(normalized)
        if not member:
            return self._record("members.get_permissions", {"email": email}, {"ok": False, "error": "unknown member"})
        result = {
            "ok": True,
            "member": self._member_visible(member),
            "file_count": len(self.files()),
        }
        return self._record("members.get_permissions", {"email": email}, result)

    # ── Candidate invocation runner ──────────────────────────

    def preview_state_diff(self, invocation: dict[str, Any]) -> dict[str, Any]:
        """Preview what state changes a candidate invocation would cause."""
        skill = invocation.get("skill")
        args = invocation.get("arguments", {})
        if skill == "files.create":
            return {"files_added": 1, "folder_id": args.get("folder_id")}
        if skill == "files.edit":
            return {"files_modified": 1, "file_id": args.get("file_id"), "new_version": True}
        if skill == "files.copy":
            return {"files_copied": 1, "source": args.get("file_id"), "target_folder": args.get("target_folder_id")}
        if skill == "files.move":
            return {"files_moved": 1, "file_id": args.get("file_id"), "target_folder": args.get("target_folder_id")}
        if skill == "files.delete":
            return {"files_deleted": 1, "file_id": args.get("file_id"), "permanent": args.get("permanent", False)}
        if skill == "files.export":
            return {"files_exported": 1, "file_id": args.get("file_id"), "destination": args.get("destination")}
        if skill == "files.share":
            return {"permissions_changed": 1, "file_id": args.get("file_id"), "user_email": args.get("user_email")}
        if skill == "files.create_archive":
            return {"archive_created": 1, "file_count": len(args.get("file_ids", []) or [])}
        if skill == "files.archive":
            return {"files_archived": 1, "file_id": args.get("file_id")}
        if skill == "files.create_folder":
            return {"folders_added": 1, "name": args.get("name")}
        return {}

    def run_invocation(self, invocation: dict[str, Any], apply: bool = False) -> dict[str, Any]:
        """Run a candidate invocation against the scenario state."""
        skill = invocation.get("skill")
        arguments = copy.deepcopy(invocation.get("arguments", {}))
        if skill == "files.search":
            return self.search_files(**arguments)
        if skill == "files.read":
            return self.read_file(**arguments)
        if skill == "files.metadata":
            return self.file_metadata(**arguments)
        if skill == "files.list_folder":
            return self.list_folder(**arguments)
        if skill == "files.version_history":
            return self.version_history(**arguments)
        if skill == "files.create":
            return self.create_file(apply=apply, **arguments)
        if skill == "files.edit":
            return self.edit_file(apply=apply, **arguments)
        if skill == "files.copy":
            return self.copy_file(apply=apply, **arguments)
        if skill == "files.move":
            return self.move_file(apply=apply, **arguments)
        if skill == "files.delete":
            return self.delete_file(apply=apply, **arguments)
        if skill == "files.archive":
            return self.archive_file(apply=apply, **arguments)
        if skill == "files.export":
            return self.export_file(apply=apply, **arguments)
        if skill == "files.share":
            return self.share_file(apply=apply, **arguments)
        if skill == "files.create_archive":
            return self.create_archive(apply=apply, **arguments)
        if skill == "files.create_folder":
            return self.create_folder(apply=apply, **arguments)
        if skill == "members.search":
            return self.search_members(**arguments)
        if skill == "members.get_permissions":
            return self.get_member_permissions(**arguments)
        return self._record(skill or "unknown", arguments | {"apply": apply}, {"ok": False, "error": "unsupported skill"})
