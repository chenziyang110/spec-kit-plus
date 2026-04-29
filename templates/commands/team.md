---
description: Use when you need the Codex-only `sp-teams` runtime surface from the official product entry point.
workflow_contract:
  when_to_use: You need the official Codex team/runtime surface instead of an agent-specific alias or extension-internal command.
  primary_objective: Route the operator to `sp-teams` and validate the supported runtime boundary.
  primary_outputs: Runtime entrypoint guidance and environment validation only.
  default_handoff: '`sp-teams` or the generated `sp-teams` skill surface.'
---

# Codex Team Runtime

{{spec-kit-include: ../command-partials/team/shell.md}}

Official product surface:

```text
sp-teams
```

Generated skill name: `sp-teams`

First-release boundary:

1. Codex-only
2. Requires a tmux-capable environment
3. Existing-project upgrades are optional and non-blocking

Validation:

1. Run `sp-teams`
2. Confirm `tmux` is available
3. Confirm `.specify/teams/runtime.json` exists
4. Do not treat legacy aliases as the supported product surface for this repository

## Audience

This guidance belongs to the Codex-only team/runtime surface. Do not surface these instructions through other agent integrations or treat non-Codex runtimes as the intended audience.

Agent automation should prefer the `specify-teams-mcp` MCP facade when it is configured. Keep `sp-teams` as the human/operator CLI and parity fallback surface.
