description: Use the Codex-only team/runtime surface from the official `specify` product entry point.
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
