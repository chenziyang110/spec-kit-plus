# Gemini Hook Assets

This directory contains the project-local Gemini CLI native hook assets that
`specify init --ai gemini` installs into `.gemini/hooks/`.

The hooks in this directory are intentionally thin adapters. They translate
Gemini-native hook events into the shared `specify hook ...` command surface so
workflow truth remains centralized under `src/specify_cli/hooks/`.

Managed native hook coverage:

- `SessionStart` renders active workflow orientation through `specify hook render-statusline`.
- `BeforeAgent` applies shared prompt-bypass guards and soft learning-signal warnings.
- `BeforeTool` applies shared read-boundary and inline commit-message guards.

Learning capture and terminal learning review remain explicit workflow
responsibilities. Native hooks surface friction automatically, but they do not
promote learnings or invent a terminal review decision without durable evidence.
