from __future__ import annotations

from typing import Any

from .schema import PRIMARY_IMPACTS, SCHEMA_VERSION, THREAT_CATEGORIES, THREAT_TYPES


def validate_profile(profile: dict[str, Any], adapter: Any | None = None) -> None:
    required = {"schema_version", "threat_profile_id", "threat_type", "threat_subtype", "operator", "injection", "state_overlay", "observation_refs"}
    missing = required - profile.keys()
    if missing:
        raise ValueError(f"profile missing required fields: {sorted(missing)}")
    if profile["schema_version"] != SCHEMA_VERSION:
        raise ValueError(f"unsupported schema version: {profile['schema_version']}")
    if profile["threat_type"] not in THREAT_TYPES:
        raise ValueError(f"unsupported threat type: {profile['threat_type']}")
    impact = profile.get("attack_goal", {}).get("primary_impact")
    if impact not in PRIMARY_IMPACTS:
        raise ValueError(f"unsupported primary impact: {impact}")
    category = profile.get("threat_category", "")
    if category and category not in THREAT_CATEGORIES:
        raise ValueError(f"unsupported threat category: {category}")
    injection = profile["injection"]
    if not isinstance(injection, dict) or not str(injection.get("content", "")).strip():
        raise ValueError("injection.content must be non-empty")
    if not isinstance(profile["observation_refs"], list):
        raise ValueError("observation_refs must be a list")
    if adapter is not None:
        adapter.validate_profile(profile)
