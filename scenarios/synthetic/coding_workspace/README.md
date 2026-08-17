# Synthetic Coding + Workspace Scenario

This scenario lets one agent task use both repository tools and a lightweight
workspace artifact store. It tests whether workspace notes, specs, release
drafts, and review artifacts cause unreasonable coding skill invocations.

## Layout

```text
scenarios/synthetic/coding_workspace/
  app/
    api.py
    runtime.py
    benchmark.py
    candidate_selection.py
    agent_runner.py
  data/
    state.json
    toolkits/coding_workspace.json
    skills/*.json
    tasks/<family>/*.json
    threats/<type>/*.json
    contrast_groups/*.json
  outputs/
  scripts/
```

## Tool Names

Coding component tools are prefixed with `coding.`, for example:

```text
coding.files.read
coding.pr.create
coding.release.create
```

Workspace bridge tools are prefixed with `workspace.`, for example:

```text
workspace.artifacts.list
workspace.artifacts.read
workspace.artifacts.write
workspace.artifacts.update
workspace.artifacts.delete
```

Function-call-safe aliases replace dots with double underscores.

## Case Count

The initial data contains 9 cases:

- 3 benign
- 3 ambiguous
- 3 adversarial

Threat profiles use `scenario_overlays` so one synthetic threat can apply state
changes to both Coding and Workspace.

