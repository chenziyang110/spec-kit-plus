---
description: Use when plan artifacts exist and execution needs dependency-aware tasks, guardrails, and parallelization guidance before implementation.
workflow_contract:
  when_to_use: Planning artifacts already exist and the remaining gap is concrete execution slicing rather than more design work.
  primary_objective: Produce `tasks.md` with dependency ordering, guardrail carry-forward, execution batches, and join points.
  primary_outputs: '`FEATURE_DIR/task-index.json` as the canonical task graph for standard/heavy or any UI-bearing work plus rendered `tasks.md`; light non-UI leader-direct work may use only `tasks.md`. `handoff-to-tasks.json` is a compact agent transition when compatibility requires it. Worker packets are compiled just in time by `sp-implement`; task-generation lane records exist only when lanes were actually delegated.'
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

1. Run `{SCRIPT}` to resolve `FEATURE_DIR` and prerequisites without task writes, then enter `tasks` through the deterministic `specify-runtime workflow transition` command. The CLI owns phase state; keep implementation blocked until this task-generation stage completes.
2. Read `plan-contract.json` first, reuse its context capsule and referenced spec obligations, and open project-facing or live files only for named required references or stale evidence.
3. Preserve complete-first scope and map every `CA-###`, `MP-*`, preserved create/scaffold or other capability operation, reference-fidelity item, and user-observable UI/TUI/CLI/API/runtime path before finalizing `tasks.md`. Every UI-bearing task—not only screenshot-driven work—materializes the exact current object referenced by `.specify/templates/task-index-template.json#/ui_contract_schema_ref` from `.specify/templates/task-packet-template.json#/ui_contract`, then renders Design Quality Coverage plus compact per-task `Scope Boundaries` and `UI Implementation Contract` projections: work/surface/platform types, subject/audience/job, three theses, signature, approved visual ref, task-relevant reference/content/image records, `fidelity_level`, states, must-preserve/adapt/not rules, `required_evidence`, difference inventory, accepted deviations, and real-entrypoint proof under `real_entrypoint_evidence`. Required evidence includes `structure_snapshot`, `visual_capture`, `runtime_diagnostics`, and comparison/human review; synthetic component proof is insufficient.
4. Use `choose_subagent_dispatch(command_name="tasks", snapshot, workload_shape)` only for isolated task-generation lanes. When lanes are delegated, write one `task-generation/lane-manifest.json` plus one result per lane under `task-generation/handoffs/`; do not duplicate the same events into evidence-index and checkpoint logs.
5. Use task-index.json as the canonical task graph for standard/heavy and every UI-bearing task set, then render `tasks.md`; only light non-UI leader-direct work may remain a compact `tasks.md`. A ready version-2 index is mandatory whenever the plan has acceptance refs: its top-level `acceptance_refs` must be the complete unique ordered list `plan-contract.json#/acceptance_refs/0..N-1`, never copied spec refs or a selected subset. Record every official entrypoint in `official_entrypoints`, a minimal complete `system_review_scenarios` matrix, and stable `review_obligations` covering every entrypoint, acceptance/capability/must-preserve/consequence/fidelity reference, changed user-observable journey, consumer surface, required UI state, wiring path, and affected regression path. Every required obligation maps to one or more scenario ids so `sp-review` can prove zero uncovered scope instead of reconstructing executable acceptance from prose. Each `acceptance_ref` must have at least one dedicated required system-review scenario whose required acceptance-source set is exactly that one ref; a broad regression scenario may be additional evidence but cannot serve as any ref's dedicated witness. Separately freeze a non-empty Human Acceptance Universe in `human_acceptance_obligations` and `human_acceptance_scenarios`: cover every new or changed requirement that a human can exercise end to end; every obligation source is one canonical task-index `acceptance_refs` value, and every scenario records a non-empty human `actor`, official entrypoint, starting state, human action, observable terminal outcome, required/optional status, Review-scenario linkage, and obligation mapping. Every required human scenario links at least one dedicated required Review scenario for its own `acceptance_ref`; require zero uncovered required human obligations. Human performs these requirement journeys later in `sp-accept`; they are not a copy of startup, wiring, diagnostics, or broad regression scenarios, so do not repeat System Review. Do not pre-generate a full worker packet for every task. Record enough task shape for `sp-implement` to compile delegated packets just in time from the current repository state.
   Set root `validation_policy` to `mode: feature_epochs`, `max_epochs: 3`, `budget_scope: implement-review`, the shared `budget_ref`, and `heavy_gate_owner: leader`. The three epochs are logical `baseline`, `convergence`, and `delivery` gates; retries, timeout recovery, and deterministic shards are attempts inside the owning gate and do not consume another epoch. Keep full-suite, build, integration, E2E, and visual gates in feature-level `validation`/task `verification`; put only cheap changed-scope checks safe to run for one Txx in that task's `task_checks`. Workers never inherit the heavy gates.
6. Run deterministic task-graph validation for coverage, dependency cycles, write-set safety, acceptance, and verification. Use agent review only when ambiguity or high-risk judgment remains; repair task-layer defects or escalate when upstream truth is missing.
7. Run `{{specify-subcmd:specify-runtime hook validate-artifacts --command tasks --feature-dir <feature-dir> --format json}}`, repair or reopen the owning upstream phase on failure, and hand off directly to `{{invoke:implement}}` only after a clean result and `next_command: /sp.implement`.

Do not edit production source or tests, migrations, or runtime configuration. This stage owns only the executable task graph and its task-generation evidence; implementation begins only in a separately invoked `{{invoke:implement}}` workflow.

## Detailed References

Read [Reference index](references/INDEX.md) before applying detailed contracts.

- [plan intake](references/plan-intake.md)
- [task generation sequence](references/task-generation-sequence.md)
- [task packet schema](references/task-packet-schema.md)
- [dependencies and parallel safety](references/dependencies-and-parallel-safety.md)
- [must preserve ledger](references/must-preserve-ledger.md)
- [review and repair](references/review-and-repair.md)
