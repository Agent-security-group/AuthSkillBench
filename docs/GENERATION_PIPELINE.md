# Generation and Labeling Pipeline

AuthSkillBench is moving to a sandbox-first generation pipeline.

The initial runtime setup is:

```text
task + sandbox environment profile + available skills
```

An agent runs in the sandbox and proposes a candidate invocation. The benchmark
then captures that candidate invocation and scores it:

```text
candidate invocation + same task/context -> Allow | Deny | Ask | Defer | Fallback
```

## Roles

### Sandbox

Provides executable state and tools. For the email MVP, the sandbox lives under:

```text
sandboxes/email/
```

It exposes agent-facing APIs such as `/agent/tools` and `/agent/invoke`.

Tool specs are data, not only code. For email they live under:

```text
sandboxes/email/data/toolkits/
```

The API loads the toolkit spec and routes those tool names to runtime handlers.
This makes the skill/tool relationship explicit: a benchmark skill can map to
one or more executable sandbox tools.

### Task Variant

Defines what the user asks for and where authorization boundaries are
underspecified or risky. Email task variants live under:

```text
sandboxes/email/data/task_variants/
```

Each variant should include:

- `authorization_boundary`;
- `underspecifications`;
- `expected_safe_behavior`;
- `potential_risky_actions`;
- `potential_risky_outcomes`.

### Environment Profile

Defines the context slice the agent sees. Profiles encode whether observations
are benign, adversarial/untrusted, or ambiguous.

For email:

```text
sandboxes/email/data/environments/
```

### Agent

Receives the task, tool list, and sandbox observations through the runtime API.
It may propose a tool call. That proposed call is the candidate invocation.

### Oracle

Receives only the task, environment context, skill set, and captured candidate
invocation. It produces:

- expected decision;
- gold rationale;
- fallback invocation when applicable;
- hidden metadata generated from sandbox state and tool traces.

For email:

```text
sandboxes/email/app/oracle.py
```

## Current MVP

The email sandbox now uses contrast groups:

```text
trusted skill + task variant + environment profile -> agent candidate invocation -> oracle label
```

For the current MVP, `candidate_fixtures/*.json` stores captured-like candidate
calls so the end-to-end materialization pipeline can be tested before a live
planner is connected. The intended live path is still that the agent produces
the candidate invocation after running in the task/environment context.

Fixture-replay trajectories can also be generated before the live planner is
connected:

```bash
python3 -m sandboxes.email.scripts.generate_trajectories \
  --output-dir /tmp/email_sandbox_trajectories
```

Trajectory files record agent-visible inputs, tool calls, tool results,
candidate invocation, and benchmark-only oracle output. Live LLM runs should
write the same shape, but with `source` changed from `fixture_replay` to the
runner name.

The email sandbox includes a real LLM runner:

```bash
# Put DEEPSEEK_API_KEY, DEEPSEEK_MODEL, and DEEPSEEK_BASE_URL in the repo-root .env.
# See .env.example.

python3 -m sandboxes.email.scripts.run_live_agent \
  --case email_sandbox_send_ask_001 \
  --output-dir /tmp/email_sandbox_live_trajectories
```

The runner gives the model the task, observation refs, and toolkit specs, then
executes model tool calls through the sandbox API. The first tool call mapped to
the trusted skill under test becomes the captured candidate invocation for
oracle evaluation. If the model asks for clarification or takes only an
alternative action, the trajectory is still saved, but `candidate_invocation`
and `benchmark_evaluation` may be `null`.

Saved trajectories can be materialized back into benchmark samples:

```bash
python3 -m sandboxes.email.scripts.build_samples_from_trajectories \
  /tmp/email_sandbox_live_trajectories \
  --output /tmp/email_sandbox_live_samples.jsonl \
  --skip-report /tmp/email_sandbox_live_skipped.json
```

By default, trajectories without `candidate_invocation` are skipped because the
benchmark sample format labels one concrete candidate invocation.

Generate the current fixture samples:

```bash
python3 -m sandboxes.email.scripts.generate_samples \
  --output /tmp/email_sandbox_demo_samples.jsonl
```

Validate:

```bash
python3 scripts/validate_dataset.py /tmp/email_sandbox_demo_samples.jsonl
python3 scripts/build_model_inputs.py /tmp/email_sandbox_demo_samples.jsonl /tmp/email_sandbox_demo_inputs.jsonl
python3 scripts/check_model_inputs.py /tmp/email_sandbox_demo_inputs.jsonl --gold /tmp/email_sandbox_demo_samples.jsonl
```

## Acceptance Criteria

A generated sample should be accepted only if:

- the candidate invocation is plausible for an agent to propose in that context;
- the expected decision is grounded in task authority and sandbox state;
- hidden metadata is generated from runtime state, not manually invented text;
- environment profiles make trust and evidence sufficiency explicit;
- model-facing inputs do not expose gold labels or hidden metadata.
