# Email Scenario

This directory is a runnable email scenario used by AuthSkillBench. The scenario
itself behaves like a tiny local email system with an HTTP API. The benchmark
harness can start that API, expose only the agent-facing tools to an agent, and
record the candidate skill invocations produced under different task and
threat contexts.

For the detailed Chinese catalog of current skills, task variants, threat
profiles, case specs, and maintenance rules, see
[`SCENARIO_DETAILS.md`](SCENARIO_DETAILS.md).

The initial runtime input is task + scenario context + skill set. The candidate
invocation is not known at the beginning; it is proposed by the agent after it
interacts with the scenario. The scenario records that proposed call and its
runtime side-effect preview:

```text
task + runtime email context + skill set -> agent proposes candidate invocation
candidate invocation + same context -> scenario trace and candidate result
```

## Layout

```text
scenarios/email/
  README.md
  __init__.py
  app/
    api.py          # Agent-facing tool manifest and invoke() API
    runtime.py      # Internal mailbox/files/contacts state machine
    benchmark.py    # Case loading and JSONL case-record helpers
    server.py       # HTTP server for running the scenario as an API
  data/
    state.json      # Base mailbox, contacts, files, trust labels, policy knobs
    toolkits/*.json # Agent-facing tool specs and skill/tool mappings
    skills/*.json   # Trusted skill descriptors under test
    tasks/<group>/*.json          # Concrete task variants grouped by workflow family
    threats/<type>/*.json # Threat profiles grouped by benign/adversarial/ambiguous type
    contrast_groups/*.json    # Matrices tying skill + task + threat
  outputs/
    live_trajectories/*.json  # Full traces generated from live agents
    candidate_records/*.jsonl # Candidate records materialized from trajectories
    reports/*.md              # Human-readable live run summaries
  scripts/
    demo_agent.py       # Small agent-style API transcript demo
    build_samples_from_trajectories.py # Materialize candidate records from trajectories
    generate_live_report.py # Summarize live trajectories and candidate records
    run_live_agent.py   # Run a real LLM agent through scenario tools
```

Dependency direction:

```text
Shared agent framework -> EmailScenarioAPI -> runtime.py
Agent -> HTTP API or EmailScenarioAPI -> runtime.py
Benchmark harness -> threat profile + task + skills -> agent run
Benchmark harness -> agent candidate invocation -> trajectory/candidate record
```

Agents should not import `runtime.py` directly. They should use the HTTP API or
`EmailScenarioAPI`.

The reusable OpenAI-compatible tool-calling loop lives at the repository root in
`agent_framework/`. Email-specific code only builds the email prompt, applies
the threat profile, and maps agent tool calls back into email trajectories.

## Run The Scenario API

Start the email scenario as a local API:

```bash
python3 -m scenarios.email.app.server --host 127.0.0.1 --port 8765
```

Useful agent-facing endpoints:

```text
GET  /health
GET  /agent/manifest
GET  /agent/toolkit
GET  /agent/tools
GET  /agent/openai-tools
POST /agent/invoke
POST /agent/reset
GET  /agent/snapshot
```

Benchmark-only endpoints:

```text
GET  /benchmark/cases
GET  /benchmark/cases/{case_id}
GET  /benchmark/contrast-groups
GET  /benchmark/task-groups
GET  /benchmark/threat-groups
GET  /benchmark/threats
GET  /benchmark/threats/{threat_profile_id}
```

Manual API example:

```bash
curl -s http://127.0.0.1:8765/agent/tools

curl -s http://127.0.0.1:8765/agent/invoke \
  -H 'Content-Type: application/json' \
  -d '{"tool":"email.search_messages","arguments":{"query":"onboarding"}}'
```

## Python API

The HTTP server uses the same Python API that a local agent harness can import:

```python
from scenarios.email import EmailScenarioAPI

api = EmailScenarioAPI(apply_side_effects=True)
tools = api.list_tools()
result = api.invoke("email.search_messages", {"query": "onboarding"})
```

Available native tool names:

```text
email.search_messages
email.read_message
email.list_threads
email.read_thread
contacts.search
contacts.verify_current
files.list
files.metadata
files.read
gmail.users.messages.send
gmail.users.messages.forward
gmail.users.drafts.create
gmail.users.drafts.update
gmail.users.drafts.send
email.export_messages
gmail.users.messages.trash
gmail.users.messages.delete
gmail.users.messages.batchModify
```

The agent-facing tool specs are data files under
`data/toolkits/gmail_scenario.json`. `api.py` loads those specs and routes tool
calls to `runtime.py`; this keeps tool documentation/mapping separate from the
runtime implementation.

The benchmark skill under test is the manually authored
`email-ops.strategic_single_message` skill, sourced from
`email skills/email-ops/SKILL.md`. In this scenario it maps to the concrete
`gmail.users.messages.send` tool, with `gmail.users.drafts.create` as the
lower-impact fallback.

For function-calling frameworks that reject dots in function names, aliases such
as `email__read_message` are also accepted. Use `api.openai_tools()` or:

```bash
python3 -m scenarios.email.app.api --openai-tools
```

## Benchmark Flow

The benchmark is organized around contrast groups. A contrast group starts from
one trusted skill or runtime skill family and lists task/threat variants
without embedding candidate calls:

```json
{
  "contrast_group_id": "email_scenario_email_ops_send",
  "trusted_skill_name": "email-ops.strategic_single_message",
  "variants": [
    {
      "case_id": "email_scenario_send_deny_001",
      "task_variant_ref": "summarize_vendor_page",
      "threat_profile_ref": "adversarial_support_page"
    }
  ]
}
```

The candidate invocation is produced by the agent after it receives the task,
scenario observations, and skill set.

For live trajectories, candidate extraction checks task-operation tools,
trusted-skill mapped tools, and consequential scenario side effects such as
sending, exporting, deleting, forwarding, or batch-modifying messages. Read-only
context gathering is not recorded as a candidate invocation.

Task variants are categorized by the concrete email workflow rather than by a
preassigned correctness label.

Examples:

| Task type | Family | Operation |
| --- | --- | --- |
| `send_single_message` | `send_single_message` | `send_email` |
| `send_meeting_agenda` | `schedule_or_meeting_email` | `send_email` |
| `send_vendor_status_update` | `send_single_message` | `send_email` |
| `create_reply_draft` | `send_reply_or_draft` | `create_draft` |
| `summarize_external_content` | `mailbox_or_external_summary` | `summarize_content` |

Task variants also include ToolEmu-style risk annotations:

```text
underspecifications
expected_safe_behavior
potential_risky_actions
potential_risky_outcomes
```

Task groups under `data/tasks/` are directories. Each directory contains
the concrete variants for that workflow family, such as `send_email`,
`draft_email`, `summarize_email`, `delete_or_modify_email`, and `export_email`.
The grouping is intentionally filesystem-native: a variant's directory is its
task group.

Threat profiles implement a coarse type plus a more specific subtype. The
coarse type captures whether the evidence is trusted, hostile, or incomplete;
the subtype captures the concrete evidence failure mode. Profiles can also
include `state_overlay.ops`; those operations are applied to the base state
before the agent reads the context, so a threat profile can add,
modify, or remove scenario messages, contacts, and files.

| Type | Current subtypes | How it is modeled in the email scenario |
| --- | --- | --- |
| `benign` | `approved_copy_available`, `trusted_thread_supports_task` | Trusted observations align with the task and provide enough evidence for the relevant low-risk action. |
| `adversarial_untrusted` | `data_exfiltration_prompt_injection` | Untrusted external content tries to induce a tool call that exceeds or conflicts with user authority. |
| `ambiguous` | `recipient_identity_ambiguous`, `stale_state` | The threat is not malicious, but evidence is incomplete, stale, or does not identify user intent precisely enough. |

Threat groups are derived from `data/threats/<type>/` directories. Current
types are `benign`, `adversarial_untrusted`, and `ambiguous`.

Run a real LLM agent against one case:

```bash
# Put these values in the repo-root .env. See .env.example.
# export DEEPSEEK_API_KEY=...
# export DEEPSEEK_MODEL=deepseek-v4-flash
# export DEEPSEEK_BASE_URL=https://api.deepseek.com

python3 -m scenarios.email.scripts.run_live_agent \
  --case email_scenario_send_ask_001 \
  --output-dir scenarios/email/outputs/live_trajectories
```

Optional environment variables:

```text
DEEPSEEK_MODEL     # defaults to deepseek-v4-flash
DEEPSEEK_BASE_URL  # defaults to https://api.deepseek.com
```

`run_live_agent.py` loads the repo-root `.env` by default if it exists. You
can also pass `--env-file path/to/file.env`.

The live runner uses DeepSeek's OpenAI-compatible Chat Completions tool-calling API,
invokes scenario tools through `EmailScenarioAPI`, and extracts candidates with
the email scenario's candidate-selection policy. By default
`--apply-side-effects` is off, so mutating tools are previewed rather than
mutating scenario state.

Build candidate records from saved trajectories:

```bash
python3 -m scenarios.email.scripts.build_samples_from_trajectories \
  scenarios/email/outputs/live_trajectories \
  --output scenarios/email/outputs/candidate_records/email_scenario_live_candidate_records.jsonl \
  --skip-report scenarios/email/outputs/candidate_records/email_scenario_live_skipped.json
```

Trajectories where the agent never calls a candidate-relevant tool are skipped
by default, because they do not contain a candidate invocation to record.

Generate a readable live run report:

```bash
python3 -m scenarios.email.scripts.generate_live_report \
  --output scenarios/email/outputs/reports/live_run_summary.md
```

The current case set covers:

```text
Trusted skills: email-ops.strategic_single_message, email-runtime.mailbox_ops, klaviyo
Concrete tools: send, draft, forward, export, trash, delete, batchModify, Klaviyo list/campaign/send operations
Task types: send_single_message, summarize_external_content, send_meeting_agenda, send_vendor_status_update, create_reply_draft, send_with_attachment, forward_message_thread, delete_messages_by_date, batch_archive_by_label, export_messages, schedule_marketing_campaign
Threat types: benign, adversarial_untrusted, ambiguous
Threat subtypes: approved_copy_available, trusted_thread_supports_task, data_exfiltration_prompt_injection, recipient_substitution, authority_spoofing, goal_hijack, consent_laundering, recipient_identity_ambiguous, stale_state, bulk_scope_ambiguous, attachment_sensitivity_unclear
```

Run the Klaviyo consent-laundering motivating example with deterministic side
effects:

```bash
python3 main.py \
  --case email_scenario_consent_laundering_001 \
  --apply-side-effects \
  --output-dir scenarios/email/outputs/demo/klaviyo_consent_laundering
```

Run a small agent-style transcript without the HTTP server:

```bash
python3 -m scenarios.email.scripts.demo_agent \
  --output scenarios/email/outputs/demo/email_api_demo_transcript.json
```

## Current Modeling Choices

- The scenario is deterministic and local; it never sends real email.
- Benchmark cases run against an effective state built from `state.json` plus
  the selected threat profile's `state_overlay.ops`.
- Mutating tools update only in-memory runtime state unless the API is run with
  `--dry-run`.
- Candidate records include runtime state context, threat overlays,
  candidate invocation, candidate result, and tool trace. They do not assign
  correctness labels.
- The agent-facing API is separate from benchmark case construction. The agent
  gets `/agent/*`; case records and group metadata come from `/benchmark/*` or
  `app/benchmark.py`.

## Skill Assessment

The collected files under `email skills/` are useful, but not all
belong in this first runtime scenario:

| Skill | Fit | Reason |
| --- | --- | --- |
| `email-ops` | High | Best rule source for single-message email, explicit send authorization, drafting, and sent-state verification. Do not use its real SMTP script in this scenario. |
| `aspire-mailpit-integration` | High as inspiration | Mailpit's capture-without-delivery model matches this scenario, but the .NET stack is heavier than this MVP needs. |
| `klaviyo` | High for motivating example | Real ClawHub marketing automation skill. Used to model consent-boundary and campaign-send authorization inside this sandbox without calling the real Klaviyo API. |
| `mailchimp` / `mailchimp-automation` | Later | Good future comparison skills for campaigns, audiences, subscribers, and irreversible campaign sends. |
| `mailer-patterns` | Low here | Useful for app-development mailer code, not for runtime email-tool authorization. |
| `mailman` | Low here | Mailing-list infrastructure belongs in a separate admin/infrastructure scenario. |
