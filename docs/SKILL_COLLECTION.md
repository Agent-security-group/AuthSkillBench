# Skill Collection

AuthSkillBench stores every benchmark skill as a local, materialized skill file.

The per-skill registry is:

```text
data/skills/registry/
```

Examples:

```text
data/skills/registry/repository_coding_agent/github__merge_pull_request.skill.json
data/skills/registry/email_communication_agent/gmail__users__messages__send.skill.json
data/skills/registry/cloud_devops_workflow/kubernetes__delete_namespaced_deployment.skill.json
data/skills/registry/data_analysis_report_agent/bigquery__jobs__query.skill.json
```

The manifest is:

```text
data/skills/registry/manifest.json
```

Scenario files such as `data/skills/repository_coding_agent.skills.json` are
scenario-level views over those local skill files. Each skill object includes a
`skill_file` pointer to its single-skill artifact.

AuthSkillBench uses two skill-schema layers inside each skill file.

## Real Tool Schema

`real_tool_schema` is extracted from public source specifications:

- GitHub REST OpenAPI operations;
- Slack Web API OpenAPI operations;
- Google Discovery API methods for Gmail, Drive, Sheets, and BigQuery;
- AWS CodeDeploy Botocore service model operations;
- Kubernetes OpenAPI operations.

The extracted source artifacts are stored in:

```text
data/skills/source_artifacts/
```

Each skill points back to one of those artifacts via:

```json
{
  "source_provenance": {
    "source_type": "...",
    "source_artifact": "data/skills/source_artifacts/...",
    "source_operation": "..."
  },
  "real_tool_schema": {}
}
```

## Benchmark Projection

`benchmark_projection.arguments_schema` is the controlled agent-facing argument
view used in benchmark samples.

This layer exists because raw API schemas are often inconvenient for
authorization examples. For example, Gmail's real `users.messages.send` method
accepts a `Message` resource with RFC822 `raw` content, while an agent-facing
email skill usually exposes `to`, `subject`, `body`, and `attachments`.

When a projection differs from the raw API shape, the skill includes a note in:

```json
{
  "benchmark_projection": {
    "note": "..."
  }
}
```

## Regenerating Source Artifacts

```bash
python3 scripts/collect_real_skill_artifacts.py
python3 scripts/enrich_skill_sets_with_sources.py
python3 scripts/check_skill_sources.py
```

The benchmark samples remain stable because they reference the projection layer,
while the source artifact layer provides auditability for the claim that the
skills are grounded in real tools/APIs.

## No Constructed Skills

The benchmark should not contain hand-constructed `local.*` skills. If a skill
cannot be traced to a downloaded source artifact, it should not appear in the
scenario skill set.

Enforce this with:

```bash
python3 scripts/check_skill_sources.py
```
