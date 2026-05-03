# Claude Hook Assets

This directory contains the project-local Claude Code native hook assets that
`specify init --ai claude` installs into `.claude/hooks/`.

The hooks in this directory are intentionally thin adapters. They translate
Claude-native hook events into the shared `specify hook ...` command surface so
workflow truth remains centralized under `src/specify_cli/hooks/`.

Managed native hook coverage:

- `SessionStart` renders active workflow orientation through `specify hook render-statusline`.
- `SessionStart` renders active workflow orientation and bounded resume cues.
- `SessionStart` injects the structured recovery summary for active resumable workflows.
- `UserPromptSubmit` applies shared prompt-bypass guards and workflow-policy checks.
- `UserPromptSubmit` handles prompt-entry phase drift with a redirect-first workflow-policy response.
- `PreToolUse` applies shared workflow-policy checks, read-boundary checks, and inline commit-message guards.
- Repeated or explicit phase jumps are blocked by the shared workflow policy.
- `PostToolUse` applies session-state drift checks, soft learning-signal warnings, and compaction refresh guidance.
- `Stop` applies context checkpoint monitoring, compaction refresh, bounded resume cues, and soft learning-signal warnings.

Learning capture and terminal learning review remain explicit workflow
responsibilities. Native hooks surface friction automatically, but they do not
promote learnings or invent a terminal review decision without durable evidence.
