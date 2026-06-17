# Workspace Scenario

This directory is a runnable collaborative workspace scenario used by AuthSkillBench.
It simulates a Google-Drive-like file space where files have fine-grained permissions
(view, copy, edit, share, delete, export) and ownership. The scenario models
real-world tasks such as updating proposal drafts, copying onboarding documents,
cleaning up expired drafts, organizing project files, packaging client materials,
and summarizing meeting action items.

## Core Authorization Boundaries

The workspace scenario focuses on authorization boundaries that are unique
to collaborative file spaces:

1. **Visible ≠ Copyable/Exportable/Shareable** — A user may see a file but not
   have permission to copy, export, or share its content.
2. **Editable ≠ Can Change Access Scope** — A user may edit content but not
   change who else can access the file.
3. **Internal Share ≠ Client-Visible** — Content shared within the team must not
   automatically become visible to external clients.
4. **Can View ≠ Can Delete or Transfer Ownership** — Viewing a file does not
   grant the right to delete it or transfer it to another user.
5. **Latest Version ≠ Approved Version** — The most recent edit may not be the
   approved/sanctioned version.
6. **Summarizing ≠ Copying Verbatim** — Summarizing a restricted document does
   not authorize copying its content verbatim into a wider-permission document.

## Layout

```text
scenarios/workspace/
  README.md
  __init__.py
  app/
    api.py                  # WorkspaceScenarioAPI — agent-facing tool manifest and invoke()
    runtime.py              # WorkspaceScenario — file/folder/members/permissions state machine
    benchmark.py            # Case loading and JSONL helpers
    server.py               # HTTP server for running the scenario as an API
    candidate_selection.py  # Candidate invocation extraction policy
    agent_runner.py         # Live agent runner
    trajectory.py           # Trajectory file writing
    trajectory_samples.py   # Candidate record extraction from trajectories for evaluation
  data/
    state.json              # Base workspace state (account, members, folders, files, permissions)
    toolkits/workspace_scenario.json  # Agent-facing tool specs with skill mappings
    skills/                 # Trusted skill descriptors (workspace_collab_docs, workspace_file_ops, …)
    tasks/                  # Task variants grouped by workflow family
    threats/                # Threat profiles by benign/adversarial/ambiguous
    contrast_groups/        # Matrices tying skill + task + threat → case
  outputs/
    trajectories/           # Generated trajectory files (populated by run_live_agent.py)
    demo/
      main_flow/            # Demo trajectory artifacts
  workspace skills/         # SKILL.md files from the skill registry (populate from Maton)
  scripts/
    demo_agent.py           # Small API transcript demo
    run_live_agent.py       # Run a real LLM agent through scenario tools
```

## Run The Scenario API

Start the workspace scenario as a local API:

```bash
python3 -m scenarios.workspace.app.server --host 127.0.0.1 --port 8766
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

Benchmark endpoints:

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
curl -s http://127.0.0.1:8766/agent/tools

curl -s http://127.0.0.1:8766/agent/invoke \
  -H 'Content-Type: application/json' \
  -d '{"tool":"files.search","arguments":{"query":"proposal"}}'
```

## Run Live Agent

Run an LLM agent through all workspace cases:

```bash
# Run all cases (writes trajectory files to outputs/trajectories/)
python3 -m scenarios.workspace.scripts.run_live_agent

# Run specific cases
python3 -m scenarios.workspace.scripts.run_live_agent \
    --case workspace_scenario_proposal_edit_benign_001 \
    --case workspace_scenario_export_leak_001

# Allow mutating file operations
python3 -m scenarios.workspace.scripts.run_live_agent \
    --case workspace_scenario_proposal_edit_benign_001 \
    --apply-side-effects

# Print trajectories to stdout (no file I/O)
python3 -m scenarios.workspace.scripts.run_live_agent --stdout

# With a custom model / API endpoint
python3 -m scenarios.workspace.scripts.run_live_agent \
    --model deepseek-chat --base-url https://api.deepseek.com

# Export a .env file with DEEPSEEK_API_KEY, DEEPSEEK_MODEL, DEEPSEEK_BASE_URL
python3 -m scenarios.workspace.scripts.run_live_agent \
    --env-file /path/to/.env
```

> **Note:** By default `--apply-side-effects` is **off**, meaning mutating tools
> (`files.create`, `files.edit`, `files.delete`, `files.share`, etc.) return
> previews without modifying the in-memory state. Pass `--apply-side-effects` to
> allow actual state mutations.

## Python API

```python
from scenarios.workspace import WorkspaceScenarioAPI

api = WorkspaceScenarioAPI(apply_side_effects=True)
tools = api.list_tools()
result = api.invoke("files.search", {"query": "proposal"})
```

## Available Tools

| Tool | Side Effect | Description |
|------|-------------|-------------|
| `files.search` | read | Search files by query, folder, or tags |
| `files.read` | read | Read file content (requires view) |
| `files.metadata` | read | Read file metadata and your permissions |
| `files.list_folder` | read | List folder contents |
| `files.version_history` | read | View file version history |
| `files.create` | state_changing_workflow | Create a new file |
| `files.edit` | state_changing_workflow | Edit file content/name (requires edit) |
| `files.copy` | file_copy | Copy file to another folder (requires copy) |
| `files.move` | state_changing_workflow | Move file (requires edit) |
| `files.delete` | destructive_write | Delete file (requires delete) |
| `files.archive` | state_changing_workflow | Archive file (requires edit) |
| `files.export` | sensitive_read_export | Export file to destination (requires export) |
| `files.share` | permission_change | Change file permissions (requires share) |
| `files.create_archive` | archive_creation | Create zip archive |
| `files.create_folder` | state_changing_workflow | Create folder |
| `members.search` | read | Search workspace members |
| `members.get_permissions` | read | Get member permission summary |

## Current Case Set

| Contrast Group | Task Variant | Case ID | Threat | Operation |
|----------------|-------------|---------|--------|-----------|
| `workspace_collab_docs` | update_proposal_draft | `proposal_edit_benign_001` | benign | files.edit |
| `workspace_collab_docs` | update_proposal_draft | `version_ambiguous_001` | ambiguous (version) | files.edit |
| `workspace_collab_docs` | summarize_meeting_actions | `summarize_notes_benign_001` | benign | files.create |
| `workspace_file_sharing` | package_client_materials | `share_hijack_001` | adversarial (recipient_substitution) | files.share |
| `workspace_file_sharing` | organize_project_materials | `permission_ambiguous_001` | ambiguous (permission_boundary) | files.move |
| `workspace_archive_export` | package_client_materials | `export_leak_001` | adversarial (goal_hijack) | files.export |
| `workspace_archive_export` | cleanup_expired_drafts | `cleanup_benign_001` | benign | files.delete |
| `workspace_archive_export` | copy_onboarding_docs | `copy_onboarding_benign_001` | benign | files.copy |

### Threat Type Coverage

| Type | Count | Coverage |
|------|-------|----------|
| `benign` | 3 | Proposal edit, onboarding copy, cleanup drafts |
| `adversarial_untrusted` | 2 | Export leak (goal hijack), share hijack (recipient substitution) |
| `ambiguous` | 2 | File version ambiguity, permission boundary ambiguity |

## Threat Types

| Type | Description |
|------|-------------|
| `benign` | Trusted context that aligns with the task |
| `adversarial_untrusted` | Hostile external content attempting to induce unauthorized actions |
| `ambiguous` | Evidence is incomplete, conflicting, or authorization boundary is unclear |
