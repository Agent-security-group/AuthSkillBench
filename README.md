# AuthSkillBench

AuthSkillBench evaluates invocation-time authorization for trusted agent skills.
The core claim is:

```text
skill-level trust does not imply invocation-time authorization.
```

The project is moving from a static seed dataset to runnable sandbox
environments. A sandbox exposes tools to an agent at runtime. The agent sees a
task, a sandbox context, and available skills, then proposes a candidate skill
invocation. The benchmark captures that candidate invocation and scores whether
it should execute.

```text
task + sandbox context + skill set -> agent proposes candidate invocation
candidate invocation + same context -> Allow | Deny | Ask | Defer | Fallback
```

## Layout

```text
docs/             Benchmark design notes and rubric.
schemas/          JSON Schema for materialized benchmark samples.
data/skills/      Skill registry and source-derived skill artifacts.
sandboxes/email/  Runnable email sandbox MVP.
scripts/          Generic validation, input-building, scoring, and utility scripts.
examples/         Prediction format example.
```

The old static dataset directories `data/cases/` and `data/samples/` have been
removed to avoid confusion with the sandbox-first layout.

## Email Sandbox

The current runnable sandbox is:

```text
sandboxes/email/
  app/             Runtime API, HTTP server, oracle, benchmark helpers.
  data/            Email state, environment profiles, and case fixtures.
  scripts/         Sandbox-specific generation and demo scripts.
```

Start the email sandbox API:

```bash
python3 -m sandboxes.email.app.server --host 127.0.0.1 --port 8765
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

List benchmark environment profiles:

```bash
curl -s http://127.0.0.1:8765/benchmark/environments
```

Evaluate a captured candidate invocation fixture:

```bash
curl -s http://127.0.0.1:8765/benchmark/evaluate-case \
  -H 'Content-Type: application/json' \
  -d '{"case_id":"email_sandbox_send_deny_001"}'
```

See [sandboxes/email/README.md](sandboxes/email/README.md) for the full email
sandbox structure and API contract.

## Generate Demo Samples

Materialize the current email sandbox fixtures into benchmark JSONL:

```bash
python3 -m sandboxes.email.scripts.generate_samples \
  --output /tmp/email_sandbox_demo_samples.jsonl
```

Validate:

```bash
python3 scripts/validate_dataset.py /tmp/email_sandbox_demo_samples.jsonl
python3 scripts/print_stats.py /tmp/email_sandbox_demo_samples.jsonl
```

Build model-facing inputs:

```bash
python3 scripts/build_model_inputs.py \
  /tmp/email_sandbox_demo_samples.jsonl \
  /tmp/email_sandbox_demo_inputs.jsonl

python3 scripts/check_model_inputs.py \
  /tmp/email_sandbox_demo_inputs.jsonl \
  --gold /tmp/email_sandbox_demo_samples.jsonl
```

The current email MVP covers one fixture for each label:

```text
Allow | Ask | Defer | Deny | Fallback
```

## Skill Registry

Check that non-local skills are backed by source artifacts:

```bash
python3 scripts/check_skill_sources.py
```

Regenerate the local per-skill registry:

```bash
python3 scripts/materialize_individual_skills.py
```
