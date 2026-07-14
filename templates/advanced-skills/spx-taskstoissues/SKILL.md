---
name: spx-taskstoissues
description: Explicit task-to-GitHub-issue export for advanced coding models. Use when a validated task graph should be published to the repository tracker with dependency intent preserved.
---

# SPX Tasks to Issues

Read `references/project-cognition.md`, using cognition intent `plan`, and
`references/issue-export-contract.md`. Resolve the active feature with the
installed prerequisite script using `--require-tasks --include-tasks`.

Confirm the user requested the external write, the target GitHub repository is
unambiguous, credentials/connector access are available, and the task graph is
current and validated. Read `task-index.json` when present, otherwise
`tasks.md`. Do not publish secrets, private evidence, internal-only paths, or
unstable draft tasks.

Check existing issues and recorded task links before creating anything. Project
each task into an actionable issue with stable task identity, outcome, scope,
dependencies, acceptance, verification, and useful feature/plan links. Preserve
dependency order using the tracker's supported representation; do not change
task meaning to fit an issue template.

Create issues through the installed deterministic exporter or GitHub connector.
Record matched or created issue IDs in the supported task metadata. On partial
failure, stop duplicate retries, report exactly which task IDs were matched,
created, or not attempted, and provide the safe retry boundary.

This workflow does not implement tasks or change planning truth.
