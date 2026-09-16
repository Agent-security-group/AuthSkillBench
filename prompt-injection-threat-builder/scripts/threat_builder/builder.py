from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .adapters import adapters, stable_token
from .catalog import InjectionSeed, seed_by_id
from .goals import SCENARIO_ALIASES, exact_predicates, get_goal, list_goals
from .operators import get_operator
from .schema import ThreatProfile
from .validate import validate_profile
from scenarios.email.app.email_specs import (
    build_attack_spec,
    business_native_payload,
    business_rhetoric_variant,
    is_compatible,
)


class UniversalThreatBuilder:
    """Construct deterministic, offline threat profiles for all primary scenarios."""

    def __init__(self, repo_root: Path | None = None, catalog_path: Path | None = None):
        self.repo_root = repo_root or Path(__file__).resolve().parents[3]
        self.catalog_path = catalog_path or Path(__file__).resolve().parents[2] / "references" / "injection-seed-catalog.md"
        self.adapters = adapters(self.repo_root)

    def build(self, scenario: str, task_ref: str, operator: str = "scope_expansion", seed_id: str = "1", params: dict[str, Any] | None = None, goal_id: str | None = None) -> dict[str, Any]:
        requested_scenario = scenario.lower()
        canonical_scenario = SCENARIO_ALIASES.get(requested_scenario, requested_scenario)
        if canonical_scenario not in self.adapters:
            raise KeyError(f"unknown scenario: {scenario}; choose one of {sorted(self.adapters)}")
        params = dict(params or {})
        selected_goal = get_goal(goal_id) if goal_id else None
        if selected_goal and SCENARIO_ALIASES.get(selected_goal.scenario, selected_goal.scenario) != canonical_scenario:
            raise ValueError(f"goal {goal_id} belongs to scenario {selected_goal.scenario}, not {scenario}")
        if selected_goal:
            operator = selected_goal.operator
        adapter = self.adapters[canonical_scenario]
        task = adapter.load_task(task_ref)
        seed: InjectionSeed = seed_by_id(self.catalog_path, seed_id)
        rendered, goal = get_operator(operator)(seed.content, task)
        email_spec = None
        email_rhetoric_variant = None
        if canonical_scenario == "email" and selected_goal:
            email_spec = build_attack_spec(selected_goal.goal_id, task)
            seed_ref = f"{seed.category}:{seed.seed_id}"
            email_rhetoric_variant = business_rhetoric_variant(seed_ref)[0]
            rendered = business_native_payload(selected_goal.goal_id, task, email_spec, seed_ref=seed_ref)
        if params.get("payload"):
            rendered = str(params["payload"])
            if canonical_scenario == "email":
                email_rhetoric_variant = "custom_payload"
        params.setdefault("task_ref", task_ref)
        token = stable_token(requested_scenario, task_ref, operator, f"{seed.category}:{seed.seed_id}", selected_goal.goal_id if selected_goal else None)
        overlay, refs = adapter.build_overlay(operator, rendered, token, params)
        attack_goal = dict(goal or {})
        if selected_goal:
            attack_goal.update(selected_goal.oracle)
            attack_goal.update({"goal_id": selected_goal.goal_id, "category": selected_goal.category, "primary_impact": selected_goal.category})
            success_predicate, utility_predicate = exact_predicates(canonical_scenario, selected_goal, task)
            # Predicates that act on the generated carrier must name the exact
            # object inserted into this run. Resolve those references only after
            # the adapter has created its deterministic overlay.
            bindings = {
                "__THREAT_MESSAGE_ID__": next((ref.split(":", 1)[1] for ref in refs if ref.startswith("message:")), None),
                "__THREAT_MESSAGE_REF__": next((ref for ref in refs if ref.startswith("message:")), None),
                "__THREAT_RESULT_ID__": next((ref.split(":", 1)[1] for ref in refs if ref.startswith("result:")), None),
                "__THREAT_ISSUE_ID__": next((ref.split(":", 1)[1] for ref in refs if ref.startswith("issue:")), None),
                "__THREAT_FILE_ID__": next((ref.split(":", 1)[1] for ref in refs if ref.startswith("file:")), None),
            }
            def bind(value: Any) -> Any:
                if isinstance(value, str) and value in bindings and bindings[value]:
                    return bindings[value]
                if isinstance(value, dict):
                    return {key: bind(item) for key, item in value.items()}
                if isinstance(value, list):
                    return [bind(item) for item in value]
                return value
            def replace_tokens(value: Any) -> Any:
                if isinstance(value, str):
                    for placeholder, resolved in bindings.items():
                        if resolved:
                            value = value.replace(placeholder, str(resolved))
                    return value
                if isinstance(value, dict):
                    return {key: replace_tokens(item) for key, item in value.items()}
                if isinstance(value, list):
                    return [replace_tokens(item) for item in value]
                return value
            # Bind carrier IDs before freezing the profile. This keeps the
            # payload, attack spec, and executable predicate on one value.
            rendered = replace_tokens(rendered)
            overlay = replace_tokens(overlay)
            email_spec = replace_tokens(email_spec) if email_spec is not None else None
            success_predicate = bind(success_predicate)
            utility_predicate = bind(utility_predicate)
            for predicate in (success_predicate, utility_predicate):
                for rule in predicate.get("rules", []):
                    rule["task_variant_ref"] = task_ref
        else:
            success_predicate = {"kind": "exact_tool_call_v1", "rules": []}
            utility_predicate = {"kind": "exact_tool_call_v1", "rules": []}
        scenario_overlays = {}
        if canonical_scenario == "workspace":
            scenario_overlays = {"workspace": {"state_overlay": overlay, "observation_refs": refs}}
        profile = ThreatProfile(
            threat_profile_id=f"generated_{requested_scenario}_{task_ref}_{selected_goal.goal_id if selected_goal else operator}_{seed.seed_id}_{token}",
            threat_subtype=operator,
            attack_goal=attack_goal,
            operator=operator,
            injection={"source_kind": refs[0].split(":", 1)[0], "placement": "body", "content": rendered, "carrier_ref": refs[0] if refs else None},
            state_overlay=overlay,
            observation_refs=refs,
            success_predicate=success_predicate,
            utility_predicate=utility_predicate,
            generation_metadata={"seed": int(seed.seed_id), "seed_ref": f"{seed.category}:{seed.seed_id}", "seed_category": seed.category, "seed_title": seed.title, "email_rhetoric_variant": email_rhetoric_variant, "generator_version": "universal-threat-builder.v0.5", "attempt": 1},
            scenario=requested_scenario,
            task_variant_ref=task_ref,
            threat_category=selected_goal.category if selected_goal else "",
            description=f"Generated {operator} injection from catalog seed {seed.seed_id}: {seed.title}.",
            context_properties={"evidence_state": "generated_adversarial", "instruction_trust": "untrusted", "supports_autonomous_execution": False},
            source_metadata={"catalog_path": str(self.catalog_path), "delivery": seed.delivery, "source_text_is_untrusted": True},
            scenario_overlays=scenario_overlays,
        ).to_dict()
        if email_spec is not None:
            email_spec["carrier_ref"] = refs[0] if refs else None
            profile["email_attack_spec"] = email_spec
            profile["carrier_ref"] = email_spec["carrier_ref"]
            profile["authorized_object_ref"] = email_spec.get("authorized_object_ref")
            profile["unsafe_target_ref"] = email_spec.get("unsafe_target_ref")
        if params.get("success_predicate"):
            profile["success_predicate"] = params["success_predicate"]
        profile["generation_metadata"]["validation_status"] = "draft_requires_live_protocol"
        validate_profile(profile, adapter)
        return profile

    def build_goal_matrix(self, category: str, scenario: str, task_ref: str, seed_id: str = "contextual:1", params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Generate every currently defined goal for one CIA/scenario slice."""
        goals = list_goals(category, scenario)
        if not goals:
            raise ValueError(f"no goals defined for category={category}, scenario={scenario}")
        return [
            self.build(scenario, task_ref, seed_id=seed_id, params=params, goal_id=goal.goal_id)
            for goal in goals
            if canonical_compatible(scenario, goal.goal_id, task_ref)
        ]


def canonical_compatible(scenario: str, goal_id: str, task_ref: str) -> bool:
    if SCENARIO_ALIASES.get(scenario.lower(), scenario.lower()) != "email":
        return True
    return is_compatible(goal_id, task_ref)


def profile_digest(profile: dict[str, Any]) -> str:
    import json
    payload = json.dumps(profile, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()
