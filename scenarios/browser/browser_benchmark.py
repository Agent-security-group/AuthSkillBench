# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from typing import Any, List, Dict, Optional

from .app.benchmark import list_cases, load_case, list_threat_profiles


class TaskType(Enum):
    NORMAL_AUTHORIZED = "normal_authorized"
    TARGET_DEVIATION = "target_deviation"
    AMBIGUOUS_AUTHORIZATION = "ambiguous_authorization"
    ALTERNATIVE_AVAILABLE = "alternative_available"
    TARGET_SHIFTED = "target_shifted"
    SCOPE_EXPANSION = "scope_expansion"
    SUBSTITUTABLE = "substitutable"


class EnvType(Enum):
    BENIGN = "benign"
    UNTRUSTED = "untrusted"
    AMBIGUOUS = "ambiguous"


class AuthDecision(Enum):
    ALLOW = "Allow"
    DENY = "Deny"
    ASK = "Ask"
    DEFER = "Defer"


class RiskType(Enum):
    CONFIDENTIALITY_BREACH = "confidentiality_breach"
    WRONG_TARGET = "wrong_target"
    SCOPE_EXPANSION = "scope_expansion"


@dataclass
class CandidateInvocation:
    skill_name: str
    parameters: Dict[str, Any]
    invocation_reason: str
    trigger_observation: str


@dataclass
class Context:
    task_description: str
    task_type: TaskType
    environment_description: str
    environment_type: EnvType


@dataclass
class BenchmarkSample:
    sample_id: str
    scenario_context: str
    candidate_invocation: CandidateInvocation
    oracle_decision: AuthDecision
    recommended_action: str
    risk_type: Optional[RiskType]
    task_type: TaskType
    env_type: EnvType


def _task_type_from_str(task_type_str: str) -> TaskType:
    mapping = {
        "normal_authorized": TaskType.NORMAL_AUTHORIZED,
        "target_deviation": TaskType.TARGET_DEVIATION,
        "target_shifted": TaskType.TARGET_SHIFTED,
        "ambiguous_authorization": TaskType.AMBIGUOUS_AUTHORIZATION,
        "ambiguous_authorized": TaskType.AMBIGUOUS_AUTHORIZATION,
        "alternative_available": TaskType.ALTERNATIVE_AVAILABLE,
        "substitutable": TaskType.SUBSTITUTABLE,
        "scope_expansion": TaskType.SCOPE_EXPANSION,
    }
    return mapping.get(task_type_str, TaskType.NORMAL_AUTHORIZED)


def _env_type_from_str(env_type_str: str) -> EnvType:
    mapping = {
        "benign": EnvType.BENIGN,
        "untrusted": EnvType.UNTRUSTED,
        "adversarial_untrusted": EnvType.UNTRUSTED,
        "ambiguous": EnvType.AMBIGUOUS,
    }
    return mapping.get(env_type_str, EnvType.BENIGN)


def _auth_decision_from_str(decision_str: str) -> AuthDecision:
    mapping = {
        "allow": AuthDecision.ALLOW,
        "deny": AuthDecision.DENY,
        "ask": AuthDecision.ASK,
        "defer": AuthDecision.DEFER,
    }
    return mapping.get(decision_str.lower(), AuthDecision.ASK)


def _risk_type_from_str(risk_str: str) -> Optional[RiskType]:
    if not risk_str:
        return None
    mapping = {
        "confidentiality_breach": RiskType.CONFIDENTIALITY_BREACH,
        "wrong_target": RiskType.WRONG_TARGET,
        "scope_expansion": RiskType.SCOPE_EXPANSION,
    }
    return mapping.get(risk_str)


def generate_browser_benchmark() -> List[BenchmarkSample]:
    samples = []
    case_counter = 1

    cases = list_cases()
    threat_profiles = {tp["threat_profile_id"]: tp for tp in list_threat_profiles()}

    for case in cases:
        case_id = case["case_id"]
        contrast_group_id = case["contrast_group_id"]
        task_variant_ref = case.get("task_variant_ref")
        threat_profile_ref = case.get("threat_profile_ref")

        try:
            loaded_case = load_case(case_id)
        except Exception as e:
            continue

        task = loaded_case.get("task", {})
        threat = loaded_case.get("threat_profile", {})
        trusted_skill = loaded_case.get("trusted_skill", {})

        task_type_str = task.get("task_type", "normal_authorized")
        task_type = _task_type_from_str(task_type_str)

        env_type_str = threat.get("threat_type", "benign")
        env_type = _env_type_from_str(env_type_str)

        risk_type_str = threat.get("risk_type")
        risk_type = _risk_type_from_str(risk_type_str)

        expected_auth = threat.get("expected_authorization", "allow")
        oracle_decision = _auth_decision_from_str(expected_auth)

        skill_name = trusted_skill.get("skill_name", "web_browsing")

        task_description = task.get("description", task.get("task_description", ""))
        threat_description = threat.get("description", "")

        target_urls = task.get("target_urls", [])
        parameters = {"target_url": target_urls[0]} if target_urls else {}

        invocation_reason = f"Task: {task_description}, Skill: {skill_name}"
        trigger_observation = f"Case: {case_id}, Threat: {threat_description}"

        invocation = CandidateInvocation(
            skill_name=skill_name,
            parameters=parameters,
            invocation_reason=invocation_reason,
            trigger_observation=trigger_observation
        )

        action_map = {
            "allow": f"Execute {skill_name} action",
            "deny": f"Reject {skill_name} action - {risk_type_str if risk_type_str else 'security concern'}",
            "ask": f"Confirm {skill_name} action with user",
            "defer": f"Defer {skill_name} action pending authorization",
        }
        recommended_action = action_map.get(expected_auth, f"Process {skill_name} action")

        scenario_context = f"Task: {task_description}\nThreat: {threat_description}\nSkill: {skill_name}"

        sample = BenchmarkSample(
            sample_id=f"browser_scenario_{case_counter:03d}",
            scenario_context=scenario_context,
            candidate_invocation=invocation,
            oracle_decision=oracle_decision,
            recommended_action=recommended_action,
            risk_type=risk_type,
            task_type=task_type,
            env_type=env_type
        )
        samples.append(sample)
        case_counter += 1

    return samples


def save_to_json(samples: List[BenchmarkSample], output_path: str = "benchmark_browser.json") -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    def serialize(obj: Any) -> Any:
        if isinstance(obj, Enum):
            return obj.value
        if isinstance(obj, (CandidateInvocation, Context)):
            return asdict(obj)
        if isinstance(obj, BenchmarkSample):
            d = asdict(obj)
            return {k: serialize(v) for k, v in d.items()}
        if isinstance(obj, dict):
            return {k: serialize(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [serialize(item) for item in obj]
        return obj

    data = [serialize(sample) for sample in samples]

    with output.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)


def main() -> None:
    samples = generate_browser_benchmark()
    print(f"Generated {len(samples)} browser benchmark samples")
    print("\nSample structure:")
    for i, sample in enumerate(samples[:3], 1):
        print(f"\n--- Sample {i}: {sample.sample_id} ---")
        print(f"Task Type: {sample.task_type.value}")
        print(f"Env Type: {sample.env_type.value}")
        print(f"Oracle Decision: {sample.oracle_decision.value}")
        print(f"Risk Type: {sample.risk_type.value if sample.risk_type else 'None'}")
        print(f"Skill: {sample.candidate_invocation.skill_name}")
        print(f"Target URL: {sample.candidate_invocation.parameters.get('target_url')}")

    save_to_json(samples)
    print(f"\nSaved to benchmark_browser.json")


if __name__ == "__main__":
    main()
