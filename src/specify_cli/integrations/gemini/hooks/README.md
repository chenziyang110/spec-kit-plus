# Gemini Hook Assets

This directory contains the project-local Gemini CLI native hook assets that
`{{specify-subcmd:init --ai gemini}}` installs into `.gemini/hooks/`.

The hooks in this directory are intentionally thin adapters. They translate
Gemini-native hook events into the shared `{{specify-subcmd:hook --help}}` command surface so
workflow truth remains centralized under `src/specify_cli/hooks/`.

Managed native hook coverage:

- `SessionStart` renders active workflow orientation and bounded resume cues.
- `SessionStart` injects the structured recovery summary for active resumable workflows.
- `BeforeAgent` applies shared prompt-bypass guards, workflow-policy checks, and soft learning-signal warnings.
- `BeforeAgent` handles prompt-entry phase drift with a redirect-first workflow-policy response.
- `BeforeTool` applies shared workflow-policy checks, read-boundary checks, and inline commit-message guards.
- `BeforeTool` validates structured write paths through the pinned project runtime's `assets check --path-only`, including ordinary work without an active workflow.
- `AfterAgent` checks the task's exact written paths and bounded Git delta, including outputs from shell tools. Asset violations deny completion until repaired; unavailable checks are reported explicitly.
- Repeated or explicit phase jumps are blocked by the shared workflow policy.

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
Gemini's `AfterAgent` event supplies asset closeout. It does not replace the
workflow's durable terminal evidence or learning review.
