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

Defines the context slice the agent sees. Profiles encode a coarse evidence
type (`benign`, `adversarial_untrusted`, or `ambiguous`) and a concrete subtype
such as `data_exfiltration_prompt_injection`, `recipient_identity_ambiguous`,
or `stale_state`.

Email profiles may also carry a `state_overlay` with deterministic operations
such as `upsert_message`, `update_contact`, or `upsert_file`. The benchmark
runtime applies this overlay to the base sandbox state before exposing tools to
the agent or building case-record observations.

For email:

```text
sandboxes/email/data/environments/
```

### Agent

Receives the task, tool list, and sandbox observations through the runtime API.
It may propose a tool call. That proposed call is the candidate invocation.

## Current MVP

The email sandbox now uses contrast groups:

```text
trusted skill + task variant + environment profile -> agent candidate invocation -> candidate record
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
and candidate invocation. Live LLM runs should write the same shape, but with
`source` changed from `fixture_replay` to the runner name.

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
the trusted skill under test becomes the captured candidate invocation. If the
model asks for clarification or takes only an alternative action, the trajectory
is still saved, but `candidate_invocation` may be `null`.

Saved trajectories can be materialized back into candidate records:

```bash
python3 -m sandboxes.email.scripts.build_samples_from_trajectories \
  /tmp/email_sandbox_live_trajectories \
  --output /tmp/email_sandbox_live_candidate_records.jsonl \
  --skip-report /tmp/email_sandbox_live_skipped.json
```

By default, trajectories without `candidate_invocation` are skipped because the
candidate-record format centers one concrete candidate invocation.

Generate the current fixture case records:

```bash
python3 -m sandboxes.email.scripts.generate_samples \
  --output /tmp/email_sandbox_case_records.jsonl
```

## Acceptance Criteria

A generated email sandbox case or trajectory should be accepted only if:

- the candidate invocation is plausible for an agent to propose in that context;
- environment overlays produce the messages, contacts, files, or policy state
  needed for the case;
- candidate results and traces are generated from runtime state, not manually
  invented text;
- environment profiles make trust and evidence sufficiency explicit;
- live and fixture trajectories use the same tool/runtime surfaces.
