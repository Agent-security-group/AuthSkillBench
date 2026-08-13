# Synthetic Scenarios

Synthetic scenarios combine two scenario domains inside one task without
modifying the original single-scenario runtimes.

Each combination has its own `app/`, `data/`, `outputs/`, and `scripts/`
folders. The synthetic layer owns:

- tool namespacing, such as `email.gmail.users.messages.send` or
  `coding.files.write`;
- cross-scenario task and threat definitions;
- combined traces and candidate invocation selection;
- lightweight bridge state when needed, such as workspace artifacts.

Current combinations:

| Directory | Components | Purpose |
| --- | --- | --- |
| `email_browser/` | Email + Browser | Web context can influence email actions. |
| `coding_workspace/` | Coding + Workspace | Workspace artifacts can influence repo actions. |

The original `scenarios/Email`, `scenarios/browser`, and `scenarios/coding`
directories remain independent. Synthetic scenarios call or adapt them through a
small facade.

