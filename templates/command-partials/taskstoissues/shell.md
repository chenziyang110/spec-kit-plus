{{spec-kit-include: ../common/user-input.md}}

## Objective

Project the current task plan onto GitHub issues without losing execution ordering, dependency intent, or repository targeting accuracy.

## Context

- Primary inputs: `tasks.md`, the active feature context, and the current Git remote.
- This command assumes the repository remote is a GitHub URL and that issue creation is permitted through the configured GitHub surface.
- The issue projection should stay downstream of the planning workflow rather than becoming a parallel source of truth.

## Process

- Resolve the active feature and task artifacts.
- Confirm the repository remote targets GitHub.
- Create issues that mirror the current task graph closely enough to drive follow-on execution.

## Output Contract

- Produce GitHub issues that align with the active task breakdown.
- Preserve execution intent well enough that later implementation work can follow the issue set without losing the original task structure.
- Abort cleanly if the remote or tooling boundary makes issue creation unsafe.

## Guardrails

- Do not create issues for non-GitHub remotes.
- Do not continue if the target repository cannot be matched to the configured remote.
- Do not treat generated issues as permission to ignore later task-plan updates.
