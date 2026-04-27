# Claude Hook Assets

This directory contains the project-local Claude Code native hook assets that
`specify init --ai claude` installs into `.claude/hooks/`.

The hooks in this directory are intentionally thin adapters. They translate
Claude-native hook events into the shared `specify hook ...` command surface so
workflow truth remains centralized under `src/specify_cli/hooks/`.

Managed native hook coverage:

- `SessionStart` renders active workflow orientation through `specify hook render-statusline`.
- `UserPromptSubmit` applies shared prompt-bypass guards.
- `PreToolUse` applies shared read-boundary and inline commit-message guards.
- `PostToolUse` applies session-state drift checks and soft learning-signal warnings.
- `Stop` applies context checkpoint monitoring and soft learning-signal warnings.

Learning capture and terminal learning review remain explicit workflow
responsibilities. Native hooks surface friction automatically, but they do not
promote learnings or invent a terminal review decision without durable evidence.
