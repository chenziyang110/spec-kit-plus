---
name: spx-implement
description: Lean implementation workflow for advanced coding models. Use for ready tasks, adaptive direct or native-subagent execution, and evidence-backed feature completion.
---

# SPX Implement

Read `references/project-cognition.md`, using cognition intent `implement`.
Read `references/execution-contract.md`. Read `references/worker-contract.md`
only when delegating. Read `references/consequence-gate.md` only on its triggers.
Read `references/ui-quality-gate.md` when any ready task is UI-bearing.

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
feature workspace exists. Use `$spx-implement-teams` only when durable Codex
team state is explicitly needed. Independent lane closeout belongs to
`$spx-integrate`.

For UI-bearing work, consume the compiled task `ui_contract`; do not reconstruct
design intent from task prose. Run the real surface, capture and visually inspect
the required viewport/state matrix, repair drift, and recapture. Record behavior
checks separately from visual/interaction acceptance. Missing or bootstrap
design sources route to `$spx-design`; unavailable comparison remains
`pending-human-review`, never an implicit pass.

After verified repository changes, close out cognition with canonical workflow
`implement`. Report changed files, checks actually run, failures or skipped
checks, and residual risk. Never claim completion without fresh evidence.
