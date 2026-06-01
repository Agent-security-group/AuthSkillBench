# AuthSkillBench

AuthSkillBench studies invocation-time behavior for trusted agent skills in
runnable scenarios with threat profiles. The core claim is:

```text
skill-level trust does not imply invocation-time authorization.
```

The project is moving from a static, label-first dataset to runnable scenarios
with threat profiles. A scenario exposes tools to an agent at runtime. The agent sees a
task, a scenario context, and available skills, then proposes a candidate skill
invocation. The benchmark records that candidate invocation, its runtime result,
and the tool trace for later analysis.

```text
task + scenario context + skill set -> agent proposes candidate invocation
candidate invocation + same context -> runtime trace + candidate record
```

## Layout

```text
agent_framework/ Reusable OpenAI-compatible tool-calling agent runner.
docs/             Benchmark design and generation notes.
scenarios/email/  Runnable email scenario MVP.
```

The old static dataset directories `data/cases/` and `data/samples/`, plus the
old label-only scoring scripts, root-level skill registry, and unrelated assets
have been removed to avoid confusion with the scenario-first layout.

## Email Scenario

The current runnable scenario is:

```text
scenarios/email/
  app/             Runtime API, HTTP server, and case/trajectory helpers.
  data/            Input state, task/threat profiles, skills, and case specs.
  outputs/         Generated trajectories and JSONL records.
  scripts/         Scenario-specific generation and demo scripts.
```

Start the email scenario API:

```bash
python3 -m scenarios.email.app.server --host 127.0.0.1 --port 8765
```

Inspect agent-facing tools:

```bash
curl -s http://127.0.0.1:8765/agent/tools
```

Invoke a tool:

```bash
curl -s http://127.0.0.1:8765/agent/invoke \
  -H 'Content-Type: application/json' \
  -d '{"tool":"email.search_messages","arguments":{"query":"onboarding"}}'
```

List benchmark threat profiles:

```bash
curl -s http://127.0.0.1:8765/benchmark/threats
```

See [scenarios/email/README.md](scenarios/email/README.md) for the full email
scenario structure and API contract.

## Run The Live Email Agent

Run the deterministic end-to-end demo without an external model:

```bash
python3 main.py
```

This demonstrates loading a scenario case, assembling task/skill/threat context,
running the shared tool-calling agent framework against the local email scenario
runtime, extracting a candidate invocation, and writing demo artifacts under
`scenarios/email/outputs/demo/`.

Run a real LLM agent and then materialize candidate records from its
trajectories:

```bash
python3 -m scenarios.email.scripts.run_live_agent \
  --output-dir scenarios/email/outputs/live_trajectories

python3 -m scenarios.email.scripts.build_samples_from_trajectories \
  scenarios/email/outputs/live_trajectories \
  --output scenarios/email/outputs/candidate_records/live_candidate_records.jsonl \
  --skip-report scenarios/email/outputs/candidate_records/live_skipped.json

python3 -m scenarios.email.scripts.generate_live_report \
  --output scenarios/email/outputs/reports/live_run_summary.md
```

The email scenario currently records candidate calls and runtime effects; it
does not assign correctness labels.

The shared cross-scenario risk impact taxonomy is documented in
[docs/RISK_TAXONOMY.md](docs/RISK_TAXONOMY.md).
