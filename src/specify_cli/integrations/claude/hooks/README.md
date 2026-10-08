# Claude Hook Assets

This directory contains the project-local Claude Code native hook assets that
`{{specify-subcmd:init --ai claude}}` installs into `.claude/hooks/`.

The hooks in this directory are intentionally thin adapters. They translate
Claude-native hook events into the shared `{{specify-subcmd:hook --help}}` command surface so
workflow truth remains centralized under `src/specify_cli/hooks/`.

Managed native hook coverage:

- `SessionStart` renders active workflow orientation through `{{specify-subcmd:hook render-statusline}}`.
- `SessionStart` renders active workflow orientation and bounded resume cues.
- `SessionStart` injects the structured recovery summary for active resumable workflows.
- `SessionStart` warns when a personal Claude workflow skill (`sp-*` / `spx-*`) shadows a same-named project-installed skill and directs the user to non-destructive recovery.
- `UserPromptSubmit` applies shared prompt-bypass guards and workflow-policy checks.
- `UserPromptSubmit` handles prompt-entry phase drift with a redirect-first workflow-policy response.
- `PreToolUse` applies shared workflow-policy checks, read-boundary checks, and inline commit-message guards.
- `PreToolUse` validates structured write paths through the pinned project runtime's `assets check --path-only`, including ordinary work without an active workflow.
- Repeated or explicit phase jumps are blocked by the shared workflow policy.
- `PostToolUse` applies session-state drift checks, soft learning-signal warnings, and compaction refresh guidance.
- `Stop` applies context checkpoint monitoring, compaction refresh, bounded resume cues, and soft learning-signal warnings.
- `Stop` checks the task's exact written paths and bounded Git delta, including outputs from shell tools. Asset violations block completion until repaired; unavailable checks are reported explicitly.

The asset adapter in `.specify/bin/specify-asset-guard.py` keeps a disposable
session observation only after a relevant write or possibly mutating shell
command. Pure conversation and recognized read-only tools do not create one.
Initial dirty files are compared by content fingerprint, and explicit write
targets are always checked. Inferred paths do not grant authority to modify
another worker's files. The observation is removed after a clean or explicitly
unavailable closeout; it is not workflow state, ownership, or readiness evidence.

Learning capture and terminal learning review remain explicit workflow
responsibilities. Native hooks surface friction automatically, but they do not
promote learnings or invent a terminal review decision without durable evidence.
