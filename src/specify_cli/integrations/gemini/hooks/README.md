# Gemini Hook Assets

This directory contains the project-local Gemini CLI native hook assets that
`specify init --ai gemini` installs into `.gemini/hooks/`.

The hooks in this directory are intentionally thin adapters. They translate
Gemini-native hook events into the shared `specify hook ...` command surface so
workflow truth remains centralized under `src/specify_cli/hooks/`.

Managed native hook coverage:

- `SessionStart` renders active workflow orientation and bounded resume cues.
- `SessionStart` injects the structured recovery summary for active resumable workflows.
- `BeforeAgent` applies shared prompt-bypass guards, workflow-policy checks, and soft learning-signal warnings.
- `BeforeAgent` handles prompt-entry phase drift with a redirect-first workflow-policy response.
- `BeforeTool` applies shared workflow-policy checks, read-boundary checks, and inline commit-message guards.
- Repeated or explicit phase jumps are blocked by the shared workflow policy.

Learning capture and terminal learning review remain explicit workflow
responsibilities. Native hooks surface friction automatically, but they do not
promote learnings or invent a terminal review decision without durable evidence.
Gemini remains an ingress-only lifecycle surface until it exposes richer
post-tool or stop-time native events.
