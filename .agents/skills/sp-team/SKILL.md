---
name: "sp-team"
description: "Use the Codex-only team/runtime surface from the official `specify` product entry point."
compatibility: "Codex-only runtime surface for spec-kit projects with .specify/codex-team assets"
metadata:
  author: "github-spec-kit"
  source: "templates/commands/team.md"
---

# Codex Team Runtime

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
