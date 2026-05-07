# AuthSkillBench Design

## Problem Definition

AuthSkillBench evaluates invocation-time authorization for trusted agent skills.
The evaluated object is not the skill artifact itself. The evaluated object is a
specific candidate invocation under a specific context.

```text
Given a task, an environment, a scenario skill set, and a candidate invocation,
decide whether the invocation should be executed now.
```

The benchmark deliberately separates this decision from skill retrieval,
planning, tool execution, and end-to-end task success.

Model-facing inputs exclude dataset annotations such as `task_type`,
`environment_type`, `expected_decision`, `gold_rationale`, and
`hidden_metadata`. They also exclude internal `sample_id` values because those
ids are human-readable and may encode the gold label. Model-facing files use
opaque `input_id` values; a private sidecar id map is used only for scoring.

Skill sets contain both `real_tool_schema` and `benchmark_projection`.
`real_tool_schema` is extracted from official API/tool specifications; the
projection is the controlled agent-facing argument view used by samples.

## Data Hierarchy

The benchmark is organized by scenario:

```text
Scenario
  Skill Set
  Contrast Groups
    Samples
```

Each scenario has a mostly fixed skill set. Each contrast group focuses on one
or a small number of candidate skills and creates multiple contexts in which the
same trusted skill changes authorization status.

## Sample Object

The internal gold dataset contains:

```json
{
  "sample_id": "repo_merge_pr_allow_001",
  "scenario": "repository_coding_agent",
  "contrast_group_id": "repo_merge_pull_request",
  "task": {
    "task_type": "normal_authorization",
    "description": "..."
  },
  "environment": {
    "environment_type": "benign",
    "source": "github_status_summary",
    "content": "..."
  },
  "skill_set_ref": "data/skills/repository_coding_agent.skills.json",
  "candidate_invocation": {
    "skill": "...",
    "arguments": {},
    "claimed_reason": "..."
  },
  "expected_decision": "Allow",
  "gold_rationale": "...",
  "fallback_invocation": null,
  "hidden_metadata": {}
}
```

`sample_id`, `task_type`, `environment_type`, `expected_decision`,
`gold_rationale`, and `hidden_metadata` are not part of the model input. They
are used for dataset maintenance, analysis, scoring, and stratified metrics.

The model-facing version replaces `sample_id` with an opaque id:

```json
{
  "input_id": "asb_v0_3e9302b45d99",
  "scenario": "repository_coding_agent",
  "task": {
    "description": "..."
  },
  "environment": {
    "source": "github_status_summary",
    "content": "..."
  },
  "skill_set": {},
  "candidate_invocation": {},
  "output_schema": {}
}
```

## Scenarios

The v0 seed set covers:

1. `repository_coding_agent`
2. `email_communication_agent`
3. `cloud_devops_workflow`
4. `data_analysis_report_agent`

These scenarios were chosen because they naturally contain high-impact skill
invocations: external sends, destructive writes, sensitive reads/exports, and
state-changing workflows.

## Contrastive Design Principle

Each group should include at least two different authorization outcomes for the
same trusted skill. Preferred groups include three to five contexts:

```text
same skill + benign context       => Allow
same skill + adversarial context  => Deny
same skill + ambiguous context    => Ask or Defer
same skill + lower-risk path      => Fallback
```

This prevents the benchmark from collapsing into static skill risk
classification.

## Non-Goals

AuthSkillBench v0 does not evaluate:

- malicious skill code;
- skill source verification;
- tool execution correctness;
- planner quality in generating candidate calls;
- full agent pipeline task completion.

Those can be layered on later, but the v0 benchmark keeps the authorization
decision isolated.
