# Synthetic Coding + Workspace Details

## Integration Method

The synthetic runtime is a facade:

```text
CodingWorkspaceSyntheticRuntime
  -> CodingAPI
  -> Synthetic workspace artifact store
```

The workspace component is intentionally small. It stores artifacts with:

```text
artifact_id
title
content
sensitivity
source_refs
tags
```

This is enough to model shared specs, review notes, release drafts, copied chat
snippets, and poisoned artifacts without requiring changes to the original
coding scenario.

## Threat Shape

```json
{
  "threat_profile_id": "example",
  "threat_type": "ambiguous",
  "scenario_overlays": {
    "coding": {
      "state_overlay": {"ops": []},
      "observation_refs": []
    },
    "workspace": {
      "state_overlay": {"ops": []},
      "observation_refs": []
    }
  }
}
```

## Candidate Selection

Candidate invocation means the consequential skill/tool call that may be
unreasonable under the task authorization. The trajectory also records a
`candidate_chain` of high-impact cross-scenario calls that led to it.

