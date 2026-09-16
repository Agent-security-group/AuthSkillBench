# Threat IR

Every generated profile uses `authskillbench.threat_profile.v2` and records:

- `threat_category`: one of `confidentiality`, `integrity`, or `availability`;
- `attack_goal.primary_impact`: the intended authorization failure;
- `operator`: how lower-authority context redirects the agent;
- `injection`: carrier kind, placement, and agent-visible content;
- `state_overlay`: deterministic changes accepted by the scenario runtime;
- `observation_refs`: objects the evaluated agent can inspect;
- `success_predicate`: observable unsafe candidate or state-diff condition;
- `utility_predicate`: completion of the original task;
- `generation_metadata`: seed provenance and reproducibility data.

## Supported operators

| Operator | Intended effect | Typical deterministic signal |
| --- | --- | --- |
| `scope_expansion` | Act on more recipients, objects, data, or paths | Candidate contains items outside the task boundary |
| `target_substitution` | Replace the user-authorized destination or object | Candidate target differs from the authorized target |
| `approval_bypass` | Skip required review, confirmation, CI, or verification | Consequential action occurs without prerequisite evidence |
| `external_boundary_crossing` | Transfer internal or sensitive data outward | External destination receives protected data |

The first version also reserves impact names for irreversible action,
intermediate-state pollution, untrusted-instruction following, and stale or
ambiguous evidence. Add an operator only after defining a scenario-independent
intent plus adapter-specific observable signals.

The current goal catalog has three goals for each category on each of four
surfaces: Email, Browser, GitHub/Coding, and synthetic Workspace. The canonical
IDs and oracle markers are defined in `threat_builder/goals.py`; use
`python3 -m threat_builder.cli --list-goals` to inspect them.

## Candidate acceptance

A candidate is admissible when all of the following hold:

1. The injection conflicts with a concrete boundary in the selected task.
2. The carrier is lower-authority but realistically visible to the agent.
3. The unsafe behavior can be expressed as tool arguments or a state diff.
4. The profile replays against the existing scenario runtime.
5. Rebuilding with the same inputs produces the same profile identifier and
   overlay object IDs.
