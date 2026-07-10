---
description: Use when plan artifacts exist and execution needs dependency-aware tasks, guardrails, and parallelization guidance before implementation.
workflow_contract:
  when_to_use: Planning artifacts already exist and the remaining gap is concrete execution slicing rather than more design work.
  primary_objective: Produce `tasks.md` with dependency ordering, guardrail carry-forward, execution batches, and join points.
  primary_outputs: '`FEATURE_DIR/task-index.json` as the canonical task graph for standard/heavy work plus rendered `tasks.md`; light leader-direct work may use only `tasks.md`. `handoff-to-tasks.json` is a compact agent transition when compatibility requires it. Worker packets are compiled just in time by `sp-implement`; task-generation lane records exist only when lanes were actually delegated.'
  default_handoff: '/sp.implement for a clean completed task package; /sp.analyze only when a persisted legacy or diagnostic state explicitly records that route; /sp.plan, /sp.clarify, or /sp.deep-research when escalated remediation exposes missing upstream truth.'
handoffs:
  - label: Analyze For Consistency
    agent: sp.analyze
    prompt: Run a project analysis for consistency
    send: false
scripts:
  sh: scripts/bash/check-prerequisites.sh --json
  ps: scripts/powershell/check-prerequisites.ps1 -Json
---

{{spec-kit-include: ../command-partials/tasks/shell.md}}

{{spec-kit-include: ../command-partials/common/senior-consequence-analysis-gate.md}}

{{spec-kit-include: ../command-partials/common/agent-phase-handoff.md}}

{{spec-kit-include: ../command-partials/common/planning-cognition.md}}

[AGENT] For project-cognition-backed semantic intake, routing, audit, resume, or final-claim gates, read `references/semantic-work-contract.md`.

{{spec-kit-include: ../command-partials/common/adaptive-execution.md}}

## Main Flow

1. Run `{SCRIPT}` to resolve `FEATURE_DIR` and prerequisites, create or resume `WORKFLOW_STATE_FILE`, set `active_command: sp-tasks`, `phase_mode: task-generation-only`, and keep implementation blocked.
2. Read `plan-contract.json` first, reuse its context capsule and referenced spec obligations, and open project-facing or live files only for named required references or stale evidence.
3. Preserve complete-first scope and map every `CA-###`, `MP-*`, preserved create/scaffold or other capability operation, reference-fidelity item, and user-observable UI/TUI/CLI/API/runtime path before finalizing `tasks.md`. UI tasks carry Design Quality Coverage, `ui_fidelity_mode`, required states, `required_evidence`, difference inventory, accepted deviations, and real-entrypoint proof under `real_entrypoint_evidence`.
4. Use `choose_subagent_dispatch(command_name="tasks", snapshot, workload_shape)` only for isolated task-generation lanes. When lanes are delegated, write one `task-generation/lane-manifest.json` plus one result per lane under `task-generation/handoffs/`; do not duplicate the same events into evidence-index and checkpoint logs.
5. Use task-index.json as the canonical task graph for standard/heavy work and render `tasks.md`; light leader-direct work may remain a compact `tasks.md`. Do not pre-generate a full worker packet for every task. Record enough task shape for `sp-implement` to compile delegated packets just in time from the current repository state.
6. Run deterministic task-graph validation for coverage, dependency cycles, write-set safety, acceptance, and verification. Use agent review only when ambiguity or high-risk judgment remains; repair task-layer defects or escalate when upstream truth is missing.
7. Hand off directly to `{{invoke:implement}}` only after a clean self-audit and `next_command: /sp.implement`.

## Detailed References

Read [Reference index](references/INDEX.md) before applying detailed contracts.

- [plan intake](references/plan-intake.md)
- [task generation sequence](references/task-generation-sequence.md)
- [task packet schema](references/task-packet-schema.md)
- [dependencies and parallel safety](references/dependencies-and-parallel-safety.md)
- [must preserve ledger](references/must-preserve-ledger.md)
- [review and repair](references/review-and-repair.md)
