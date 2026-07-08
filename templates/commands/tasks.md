---
description: Use when plan artifacts exist and execution needs dependency-aware tasks, guardrails, and parallelization guidance before implementation.
workflow_contract:
  when_to_use: Planning artifacts already exist and the remaining gap is concrete execution slicing rather than more design work.
  primary_objective: Produce `tasks.md` with dependency ordering, guardrail carry-forward, execution batches, and join points.
  primary_outputs: '`FEATURE_DIR/tasks.md` and `workflow-state.md`; `task-index.json` when useful for light mode; `handoff-to-tasks.json`, `task-packets/*.json`, `task-generation/handoffs/<lane-id>.json`, `task-generation/evidence-index.json`, and `task-generation/checkpoints.ndjson` when standard/heavy mode uses delegated task-generation lanes or downstream delegated implementation needs packets.'
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

{{spec-kit-include: ../command-partials/common/semantic-work-contract.md}}

{{spec-kit-include: ../command-partials/common/adaptive-execution.md}}

## Main Flow

1. Resolve `FEATURE_DIR`, create or resume `WORKFLOW_STATE_FILE`, set `active_command: sp-tasks`, `phase_mode: task-generation-only`, and keep implementation blocked.
2. Read `spec.md`, `alignment.md`, `context.md`, `plan.md`, `plan-contract.json`, memory files, relevant learning docs, and live evidence required by project cognition advisory output.
3. Preserve complete-first scope and map every `CA-###`, `MP-*`, preserved capability operation, reference-fidelity item, and user-observable UI/TUI/CLI/API/runtime path before finalizing `tasks.md`.
4. Use `choose_subagent_dispatch(command_name="tasks", snapshot, workload_shape)` only for isolated task-generation lanes; delegated lanes must write `task-generation/handoffs/<lane-id>.json`, `task-generation/evidence-index.json`, and `task-generation/checkpoints.ndjson`.
5. Generate `tasks.md`, optional `task-index.json`, `handoff-to-tasks.json`, `task-packets/*.json`, and `workflow-state.md` with Task Guardrail Index, Reference Fidelity Mapping, implementation-guardrails phase before setup when needed, dependencies, `[P]` markers, write sets, validation commands, and join points.
6. Run the Implementation-Readiness Task Self-Audit, prepare embedded review metadata, repair task-layer defects, or escalate directly to `/sp.plan`, `/sp.clarify`, or `/sp.deep-research` when upstream truth is missing.
7. Hand off directly to `{{invoke:implement}}` only after a clean self-audit and `next_command: /sp.implement`.

## Detailed References

Read [Reference index](references/INDEX.md) before applying detailed contracts.

- [plan intake](references/plan-intake.md)
- [task generation sequence](references/task-generation-sequence.md)
- [task packet schema](references/task-packet-schema.md)
- [dependencies and parallel safety](references/dependencies-and-parallel-safety.md)
- [must preserve ledger](references/must-preserve-ledger.md)
- [review and repair](references/review-and-repair.md)
