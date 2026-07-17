# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any, Optional


class TaskType(Enum):
    NORMAL_AUTHORIZED = auto()
    TARGET_SHIFTED = auto()
    AMBIGUOUS_AUTHORIZED = auto()
    SUBSTITUTABLE = auto()
    ALTERNATIVE_AVAILABLE = auto()


class EnvType(Enum):
    BENIGN = auto()
    ADVERSARIAL_UNTRUSTED = auto()
    AMBIGUOUS = auto()


class AuthDecision(Enum):
    SHOULD_AUTHORIZE = auto()
    SHOULD_NOT_AUTHORIZE = auto()
    SHOULD_ASK_USER = auto()
    SHOULD_DEFER = auto()
    SHOULD_FALLBACK = auto()
    SHOULD_QUERY = auto()


class RiskType(Enum):
    CONFIDENTIALITY_BREACH = auto()
    WRONG_TARGET = auto()
    SCOPE_EXPANSION = auto()


@dataclass
class CandidateInvocation:
    skill: str
    claimed_reason: str
    arguments: dict[str, Any]


@dataclass
class Context:
    user_task: str
    env_context: dict[str, Any]
    tool_list: list[dict[str, Any]]


@dataclass
class BenchmarkSample:
    case_id: str
    scenario: str
    task_type: TaskType
    env_type: EnvType
    task_variant_ref: str
    threat_profile_ref: str
    context: Context
    candidate_invocation: CandidateInvocation
    oracle_decision: AuthDecision
    recommended_action: str
    risk_tags: list[RiskType]
    observation_refs: list[str] = field(default_factory=list)
    context_properties: dict[str, Any] = field(default_factory=dict)


class BenchmarkGenerator:
    def __init__(self, scenario_dir: Path):
        self.scenario_dir = scenario_dir
        self.data_dir = scenario_dir / "data"
        self.output_dir = scenario_dir / "outputs"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def load_json(self, path: Path) -> dict[str, Any]:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def compose_case_from_variant(
        self,
        case_id: str,
        task_variant_ref: str,
        threat_profile_ref: str,
    ) -> BenchmarkSample:
        task_dirs = ["search_web", "web_scraping", "browser_automation"]
        task_file = None
        for task_dir in task_dirs:
            candidate = self.data_dir / "tasks" / task_dir / f"{task_variant_ref}.json"
            if candidate.exists():
                task_file = candidate
                break
        
        if not task_file:
            raise FileNotFoundError(f"Task variant {task_variant_ref} not found in any task directory")
        
        threat_parts = threat_profile_ref.split(":")
        threat_file = self.data_dir / "threats" / "/".join(threat_parts[:-1]) / f"{threat_parts[-1]}.json"

        task_variant = self.load_json(task_file)
        threat_profile = self.load_json(threat_file)

        task_type = TaskType[task_variant["task_type"].upper()]
        env_type = EnvType[threat_profile["threat_type"].upper()]
        if env_type == EnvType.BENIGN:
            env_type_str = "benign"
        elif env_type == EnvType.ADVERSARIAL_UNTRUSTED:
            env_type_str = "adversarial_untrusted"
        else:
            env_type_str = "ambiguous"

        context = Context(
            user_task=task_variant["user_task"],
            env_context={
                "search_results": threat_profile.get("state_overlay", {}).get("ops", []),
                "threat_type": env_type_str,
            },
            tool_list=self.load_json(self.data_dir / "toolkits" / "browser_scenario.json")["tools"],
        )

        candidate_invocation = CandidateInvocation(
            skill=task_variant["candidate_invocation"]["skill"],
            claimed_reason=task_variant["candidate_invocation"]["claimed_reason"],
            arguments=task_variant["candidate_invocation"]["arguments"],
        )

        oracle_decision = AuthDecision[task_variant["expected_decision"].upper()]

        risk_tags = []
        for risk in task_variant.get("risk_tags", []):
            try:
                risk_tags.append(RiskType[risk.upper()])
            except KeyError:
                pass

        return BenchmarkSample(
            case_id=case_id,
            scenario="browser",
            task_type=task_type,
            env_type=env_type,
            task_variant_ref=task_variant_ref,
            threat_profile_ref=threat_profile_ref,
            context=context,
            candidate_invocation=candidate_invocation,
            oracle_decision=oracle_decision,
            recommended_action=task_variant.get("recommended_action", ""),
            risk_tags=risk_tags,
            observation_refs=threat_profile.get("observation_refs", []),
            context_properties=threat_profile.get("context_properties", {}),
        )

    def generate_all_samples(self) -> list[BenchmarkSample]:
        samples = []
        contrast_groups_dir = self.data_dir / "contrast_groups"

        for group_file in contrast_groups_dir.glob("*.json"):
            group_data = self.load_json(group_file)
            for variant in group_data.get("variants", []):
                case_id = variant["case_id"]
                task_variant_ref = variant["task_variant_ref"]
                threat_profile_ref = variant["threat_profile_ref"]

                sample = self.compose_case_from_variant(case_id, task_variant_ref, threat_profile_ref)
                samples.append(sample)

        return samples

    def serialize_sample(self, sample: BenchmarkSample) -> dict[str, Any]:
        def serialize_enum(e):
            if isinstance(e, Enum):
                return e.name.lower()
            return e

        def serialize(obj):
            if isinstance(obj, dict):
                return {k: serialize(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [serialize(item) for item in obj]
            elif isinstance(obj, Enum):
                return serialize_enum(obj)
            elif isinstance(obj, (Context, CandidateInvocation)):
                return serialize(obj.__dict__)
            return obj

        return {
            "case_id": sample.case_id,
            "scenario": sample.scenario,
            "task_type": serialize_enum(sample.task_type),
            "env_type": serialize_enum(sample.env_type),
            "task_variant_ref": sample.task_variant_ref,
            "threat_profile_ref": sample.threat_profile_ref,
            "context": serialize(sample.context),
            "candidate_invocation": serialize(sample.candidate_invocation),
            "oracle_decision": serialize_enum(sample.oracle_decision),
            "recommended_action": sample.recommended_action,
            "risk_tags": [serialize_enum(r) for r in sample.risk_tags],
            "observation_refs": sample.observation_refs,
            "context_properties": sample.context_properties,
        }

    def save_samples(self, samples: list[BenchmarkSample], filename: str = "benchmark_samples.json") -> None:
        serialized = [self.serialize_sample(s) for s in samples]
        with (self.output_dir / filename).open("w", encoding="utf-8") as f:
            json.dump(serialized, f, ensure_ascii=False, indent=2)
