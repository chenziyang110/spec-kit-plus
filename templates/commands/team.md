---
description: Use when you need the Codex-only `specify team` runtime surface from the official product entry point.
workflow_contract:
  when_to_use: You need the official Codex team/runtime surface instead of an agent-specific alias or extension-internal command.
  primary_objective: Route the operator to `specify team` and validate the supported runtime boundary.
  primary_outputs: Runtime entrypoint guidance and environment validation only.
  default_handoff: '`specify team` or the generated `sp-team` skill surface.'
---

# Codex Team Runtime

{{spec-kit-include: ../command-partials/team/shell.md}}

Official product surface:

```text
specify team
```

Generated skill name: `sp-team`

First-release boundary:

1. Codex-only
2. Requires a tmux-capable environment
3. Existing-project upgrades are optional and non-blocking

Validation:

1. Run `specify team`
2. Confirm `tmux` is available
3. Confirm `.specify/codex-team/runtime.json` exists
4. Do not treat `omx` or `$team` as the supported product surface for this repository

## Audience

This guidance belongs to the Codex-only team/runtime surface. Do not surface these instructions through other agent integrations or treat non-Codex runtimes as the intended audience.
