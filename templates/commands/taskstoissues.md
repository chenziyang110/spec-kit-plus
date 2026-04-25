---
description: Use when tasks.md is ready and you want actionable, dependency-aware GitHub issues generated from it.
workflow_contract:
  when_to_use: The task plan is stable enough to project onto GitHub issues instead of staying only in `tasks.md`.
  primary_objective: Convert the current task graph into actionable GitHub issues while preserving ordering and dependency intent.
  primary_outputs: GitHub issues aligned with the current `tasks.md` structure and design artifact context.
  default_handoff: Start implementation from the tracked issues or refresh the issue set after later task-plan changes.
tools: ['github/github-mcp-server/issue_write']
scripts:
  sh: scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks
  ps: scripts/powershell/check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks
---

{{spec-kit-include: ../command-partials/taskstoissues/shell.md}}

## Outline

1. Run `{SCRIPT}` from repo root and parse FEATURE_DIR and AVAILABLE_DOCS list. All paths must be absolute. For single quotes in args like "I'm Groot", use escape syntax: e.g 'I'\''m Groot' (or double-quote if possible: "I'm Groot").
1. From the executed script, extract the path to **tasks**.
1. Get the Git remote by running:

```bash
git config --get remote.origin.url
```

> [!CAUTION]
> ONLY PROCEED TO NEXT STEPS IF THE REMOTE IS A GITHUB URL

1. For each task in the list, use the GitHub MCP server to create a new issue in the repository that is representative of the Git remote.

> [!CAUTION]
> UNDER NO CIRCUMSTANCES EVER CREATE ISSUES IN REPOSITORIES THAT DO NOT MATCH THE REMOTE URL
