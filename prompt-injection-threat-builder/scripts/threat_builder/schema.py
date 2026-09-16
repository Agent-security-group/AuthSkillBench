from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


SCHEMA_VERSION = "authskillbench.threat_profile.v2"
THREAT_TYPES = {"benign", "adversarial_untrusted", "ambiguous"}
THREAT_CATEGORIES = {"confidentiality", "integrity", "availability"}
PRIMARY_IMPACTS = {
    "confidentiality", "integrity", "availability",
    "target_substitution", "scope_expansion", "approval_bypass",
    "external_boundary_crossing", "irreversible_action",
    "goal_hijack",
    "intermediate_state_pollution", "untrusted_instruction_following",
    "stale_or_ambiguous_evidence",
}


@dataclass
class ThreatProfile:
    threat_profile_id: str
    threat_subtype: str
    attack_goal: dict[str, Any]
    operator: str
    injection: dict[str, Any]
    state_overlay: dict[str, Any]
    observation_refs: list[str]
    success_predicate: dict[str, Any]
    utility_predicate: dict[str, Any]
    generation_metadata: dict[str, Any]
    scenario: str
    task_variant_ref: str
    threat_category: str = ""
    threat_type: str = "adversarial_untrusted"
    description: str = ""
    context_properties: dict[str, Any] = field(default_factory=dict)
    source_metadata: dict[str, Any] = field(default_factory=dict)
    scenario_overlays: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["schema_version"] = SCHEMA_VERSION
        # Keep schema_version first for readable, stable files.
        return {"schema_version": value.pop("schema_version"), **value}
