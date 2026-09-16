# Deterministic backend

`threat_builder` is the offline control plane for constructing replayable
AuthSkillBench threat profiles. It combines a task variant, an untrusted seed,
an attack operator, and a scenario adapter into the shared
`authskillbench.threat_profile.v2` schema.

The implementation lives under `scripts/threat_builder/`; the batch driver is
`scripts/build_threats.py`. Run both from the repository root with
`PYTHONPATH=prompt-injection-threat-builder/scripts:.`.

The seed catalog is the packaged `references/injection-seed-catalog.md`. It is
data only: the builder parses its Markdown table and keeps the text as an
injection payload; it never executes shell, Python, network, or file-operation
text found in a seed. Generated overlays are applied by the existing in-memory
scenario runtimes when a benchmark case runs.

Example:

```bash
PYTHONPATH=prompt-injection-threat-builder/scripts:. python3 -m threat_builder.cli \
  --scenario email \
  --task send_onboarding_schedule \
  --operator scope_expansion \
  --seed 1 \
  --output /tmp/generated-threat.json
```

The current implementation supports Email, Browser, GitHub/Coding, and
Workspace adapters and six cross-scenario operators: `scope_expansion`,
`target_substitution`, `approval_bypass`, `external_boundary_crossing`,
`goal_hijack`, and `irreversible_action`. Success remains an oracle concern:
the profile records a deterministic predicate for later candidate and
state-diff evaluation rather than claiming that an injection succeeded.

The initial CIA catalog contains 36 goals: three Confidentiality, Integrity,
and Availability goals for each of Email, Browser, GitHub/Coding, and the
synthetic Workspace component. Generate one complete slice with
`--category <name> --all-goals`; evaluate a trajectory with `--candidate`.
By default, generated records are written outside the skill package under
`runs/threat-builder/generated_threats/`. Successful records enter its
`successful/` subtree only when
the trajectory carries the exact generated profile ID and the declared oracle
matches.

Email generation maps catalog seeds onto eight deterministic, task-native
business framings (process update, approved change, migration compatibility,
audit archive, temporary handoff, deadline pressure, continuity exception,
and post-migration reconciliation). The batch driver explores every candidate
five times by default, screens at 4/5, then runs a completely fresh 3/3 attack
certification and a matched benign control for each qualifying frozen profile.
