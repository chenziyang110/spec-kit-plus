---
name: spx-implement
description: Lean implementation workflow for advanced coding models. Use for ready tasks, adaptive direct or team execution, independent-lane integration, and evidence-backed completion.
---

# SPX Implement

Read `references/project-cognition.md`, using cognition intent `implement`.
Read `references/execution-contract.md`. Read `references/worker-contract.md`
only when delegating. Read `references/team-and-integration.md` only when work
needs durable Codex team state or independent feature-lane integration. Read
`references/consequence-gate.md` only on its triggers.

Resolve the task-bearing feature with the installed
`.specify/scripts/bash/check-prerequisites.sh --json --require-tasks
--include-tasks` or PowerShell equivalent. Inspect the current diff, project
rules, ready tasks, and cognition-selected live paths before editing.

Execute the confirmed scope completely. Adapt stale implementation details to
the live repository while preserving user intent and recording material plan
drift. For behavior changes, establish a failing test or credible baseline when
practical. Delegate only independent, bounded work that benefits from
parallelism, isolation, or review; direct execution needs no ceremony.

Run the relevant verification for the changed behavior and risk. Fix understood
local failures; route unknown root causes to `$spx-debug`. Update existing task
status and create `implementation-summary.md` from this Skill's asset when a
feature workspace exists. For independent feature lanes, perform readiness and
overlap checks before integration rather than treating merge as automatic.

After verified repository changes, close out cognition with canonical workflow
`implement`. Report changed files, checks actually run, failures or skipped
checks, and residual risk. Never claim completion without fresh evidence.
