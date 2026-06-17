# AuthSkillBench Design

## Problem Definition

AuthSkillBench is moving toward runnable scenarios with threat profiles for studying
trusted skill invocation behavior. The evaluated object is not the skill artifact
by itself. The evaluated object is a concrete candidate invocation proposed in a
specific task and threat context.

```text
task + scenario context + available skills -> agent proposes candidate invocation
candidate invocation + same context -> runtime trace + candidate record
```

The current project does not assign built-in correctness labels. It records
candidate calls, scenario state, tool results, and trace metadata so later
analysis can ask whether the invocation was authorized, risky, over-privileged,
or harmful.

## Data Hierarchy

The scenario-first hierarchy is:

```text
Scenario
  Base State
  Skill Descriptors
  Task Groups
    Task Variants
  Threat Groups
    Threat Profiles
  Contrast Groups
    Case Specs
  Live Agent Trajectories
```

For the email scenario, `state.json` contains stable account state such as
contacts, files, and policies. Threat profiles apply deterministic
`state_overlay.ops` to create the effective mailbox state for a case.

## Runtime Case Context

A runtime case context combines one contrast-group variant into the input given
to an agent. It contains the task, threat profile, trusted skill descriptor,
and observation references. It does not contain a candidate invocation before
the agent runs.

```json
{
  "case_id": "email_scenario_export_hijack_001",
  "scenario": "email_communication_agent",
  "contrast_group_id": "email_scenario_risky_mailbox_ops",
  "trusted_skill_ref": "email_runtime_mailbox_ops",
  "skill_under_test": "email-runtime.mailbox_ops",
  "task_variant_ref": "export_support_thread",
  "threat_profile_ref": "adversarial_export_portal",
  "observation_refs": ["message:msg_support_export_thread"]
}
```

Runtime case contexts are not model gold labels. They are structured inputs for
agent execution and later candidate extraction.

## Candidate Record

A candidate record is produced from a live trajectory. It includes the
candidate invocation, the runtime result, and metadata derived from actual
scenario execution.

```json
{
  "schema_version": "authskillbench.email_candidate_record.v1",
  "case_id": "email_scenario_export_hijack_001",
  "source": "deepseek_chat_completions",
  "task_variant": {},
  "threat_profile": {},
  "candidate_invocation": {},
  "candidate_result": {},
  "runtime_metadata": {}
}
```

This shape is intentionally post-hoc-analysis friendly: a future analyzer can
classify risk outcomes such as data disclosure, data loss, wrong recipient,
unauthorized mutation, task failure, or over-privileged action after seeing the
actual candidate and runtime result.

## Current Scenarios

### Email Scenario

```text
scenarios/email/
```

It covers email tasks such as sending, drafting, forwarding, exporting,
deleting, and bulk label modification. It models benign, adversarial, and
ambiguous threats through overlay-driven mailbox state.

### Workspace Scenario

```text
scenarios/workspace/
```

It covers collaborative file-space tasks such as editing documents, copying
files, organizing folders, cleaning up drafts, packaging client materials,
and summarizing meeting notes. It models a Google-Drive-like permission
system with six permission levels (view, copy, edit, share, delete, export)
and ownership. Key authorization boundaries modeled:

- Visible != Copyable/Exportable/Shareable
- Editable != Can Change Access Scope
- Internal Share != Client-Visible
- Can View != Can Delete or Transfer Ownership
- Latest Version != Approved Version
- Summarizing Restricted Content != Copying Verbatim to Wider-Permission Docs

## Non-Goals For The Current Scenarios

The current scenarios do not attempt to provide:

- built-in oracle decisions;
- hidden gold rationales;
- label-only prompt templates;
- generic prediction scoring;
- end-to-end task-success scoring;
- malicious skill-code evaluation.

Those can be layered back later as separate analyzers, but they should not be
mixed into the runtime case construction path.
