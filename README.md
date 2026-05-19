# AuthSkillBench

AuthSkillBench studies invocation-time behavior for trusted agent skills in
runnable sandbox environments. The core claim is:

```text
skill-level trust does not imply invocation-time authorization.
```

The project is moving from a static, label-first dataset to runnable sandbox
environments. A sandbox exposes tools to an agent at runtime. The agent sees a
task, a sandbox context, and available skills, then proposes a candidate skill
invocation. The benchmark records that candidate invocation, its runtime result,
and the tool trace for later analysis.

```text
task + sandbox context + skill set -> agent proposes candidate invocation
candidate invocation + same context -> runtime trace + candidate record
```

## Layout

```text
docs/             Benchmark design and generation notes.
sandboxes/email/  Runnable email sandbox MVP.
```

The old static dataset directories `data/cases/` and `data/samples/`, plus the
old label-only scoring scripts, root-level skill registry, and unrelated assets
have been removed to avoid confusion with the sandbox-first layout.

## Email Sandbox

The current runnable sandbox is:

```text
sandboxes/email/
  app/             Runtime API, HTTP server, and case/trajectory helpers.
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

Build a runnable case record:

```bash
curl -s http://127.0.0.1:8765/benchmark/build-case \
  -H 'Content-Type: application/json' \
  -d '{"case_id":"email_sandbox_send_deny_001"}'
```

See [sandboxes/email/README.md](sandboxes/email/README.md) for the full email
sandbox structure and API contract.

## Generate Email Case Records

Materialize the current email sandbox fixtures into case-record JSONL:

```bash
python3 -m sandboxes.email.scripts.generate_samples \
  --output /tmp/email_sandbox_case_records.jsonl
```

The email sandbox currently records candidate calls and runtime effects; it
does not assign correctness labels.
