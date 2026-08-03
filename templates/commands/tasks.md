---
description: Use when plan artifacts exist and `specify-runtime tasks` must create a dependency-aware task graph, guardrails, and parallelization guidance.
workflow_contract:
  when_to_use: Planning artifacts already exist and the remaining gap is concrete execution slicing rather than more design work.
  primary_objective: Submit task definitions to `specify-runtime tasks build|upsert|set-root|finalize|handoff`, which owns `task-index.json`, the derived `tasks.md` projection, and task transition handoffs.
  primary_outputs: '`FEATURE_DIR/task-index.json` as the canonical task graph in every execution mode plus rendered `tasks.md`; light non-UI leader-direct work keeps the same CLI-owned package compact. `handoff-to-tasks.json` and `handoff-to-implement.json` are compact pointer-only transitions created only by `specify-runtime tasks handoff` when required. Worker packets are compiled just in time by `sp-implement`; task-generation lane records exist only when lanes were actually delegated.'
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
{{spec-kit-include: ../command-partials/common/run-bootstrap.md}}

{{spec-kit-include: ../command-partials/common/planning-cognition.md}}

[AGENT] For project-cognition-backed semantic intake, routing, audit, resume, or final-claim gates, read `references/semantic-work-contract.md`.

{{spec-kit-include: ../command-partials/common/adaptive-execution.md}}

[AGENT] `sp-tasks` continues the same run created for the feature. Confirm the same run with `specify-runtime run show`, then execute decomposition work only through `specify-runtime run supervise`.

## Main Flow

1. Run `{SCRIPT}` to resolve `FEATURE_DIR` and prerequisites without task writes, then enter `tasks` through the deterministic `specify-runtime workflow transition` command. The CLI owns phase state; keep implementation blocked until this task-generation stage completes.
2. Query `plan-contract.json` first through targeted `specify-runtime artifact show` JSON pointers, reuse its context capsule and referenced obligations, and query other workflow artifacts only for named stale/missing evidence.
3. Preserve complete-first scope and map every `CA-###`, `MP-*`, preserved create/scaffold or other capability operation, reference-fidelity item, and user-observable UI/TUI/CLI/API/runtime path before finalizing the task package. Every UI-bearing task—not only screenshot-driven work—supplies only its meaningful, non-default semantic fields from the contract referenced by `.specify/templates/task-index-template.json#/ui_contract_schema_ref`; `specify-runtime tasks` expands the stable current shape from `.specify/templates/task-packet-template.json#/ui_contract`. Its deterministic renderer owns Design Quality Coverage and the compact per-task `Scope Boundaries` and `UI Implementation Contract` projections. The expanded object retains `fidelity_level`, structured `required_evidence`, real-entrypoint proof, a difference inventory, and accepted deviations rather than flattening reference fidelity into prose. Required evidence includes `structure_snapshot`, `visual_capture`, `runtime_diagnostics`, and comparison/human review; synthetic component proof is insufficient.
4. Use `choose_subagent_dispatch(command_name="tasks", snapshot, workload_shape)` only for isolated task-generation lanes. Each delegated lane has no direct workflow-artifact write scope. Create an absent `task-generation/lane-manifest.json` with `specify-runtime artifact scaffold --kind task-generation-lane-manifest --path <feature-dir>/task-generation/lane-manifest.json`; query it on resume, replace the bounded `/lanes` array as a whole through fresh leased JSON-pointer patches at material joins, and patch `/status` separately at closeout. Never append inside the array or submit the manifest wholesale. Give each lane the complete runtime-owned `result submit --command tasks` argv prefix plus inline payload contract, and accept exactly one structured result per lane. A read-only evidence worker may satisfy the lane through that channel. The runtime alone materializes `task-generation/handoffs/<lane-id>.json`; do not duplicate events.
5. Create and mutate the task package only through `{{specify-subcmd:specify-runtime tasks build --feature-dir <feature-dir> --definition-json '<inline-json>' --format json}}`, `specify-runtime tasks upsert`, `specify-runtime tasks set-root`, and `specify-runtime tasks remove`; finish with `{{specify-subcmd:specify-runtime tasks finalize --feature-dir <feature-dir> --format json}}`. The CLI expands the versioned template, owns lifecycle fields, validates the graph, and atomically writes `task-index.json` and its deterministic `tasks.md` projection. Never create, patch, replace, or delete either file directly, and never materialize the inline semantic payload as a temporary JSON/Markdown file. A ready version-2 index is mandatory whenever the plan has acceptance refs: its top-level `acceptance_refs` must be the complete unique ordered list `plan-contract.json#/acceptance_refs/0..N-1`, never copied spec refs or a selected subset. Record every official entrypoint in `official_entrypoints`, a minimal complete `system_review_scenarios` matrix, and stable `review_obligations` covering every entrypoint, acceptance/capability/must-preserve/consequence/fidelity reference, changed user-observable journey, consumer surface, required UI state, wiring path, and affected regression path. Every required obligation maps to one or more scenario ids so `sp-review` can prove zero uncovered scope instead of reconstructing executable acceptance from prose. Each `acceptance_ref` must have at least one dedicated required system-review scenario whose required acceptance-source set is exactly that one ref; a broad regression scenario may be additional evidence but cannot serve as any ref's dedicated witness. Separately freeze a non-empty Human Acceptance Universe in `human_acceptance_obligations` and `human_acceptance_scenarios`: cover every new or changed requirement that a human can exercise end to end; every obligation source is one canonical task-index `acceptance_refs` value, and every scenario records a non-empty human `actor`, official entrypoint, starting state, human action, observable terminal outcome, required/optional status, Review-scenario linkage, and obligation mapping. Every required human scenario links at least one dedicated required Review scenario for its own `acceptance_ref`; require zero uncovered required human obligations. Human performs these requirement journeys later in `sp-accept`; they are not a copy of startup, wiring, diagnostics, or broad regression scenarios, so do not repeat System Review. Do not pre-generate a full worker packet for every task. Record enough task shape for `sp-implement` to compile delegated packets just in time from the current repository state.
   Set root `validation_policy` to `mode: feature_epochs`, `max_epochs: 3`, `budget_scope: implement-review`, the shared `budget_ref`, and `heavy_gate_owner: leader`. The three epochs are logical `baseline`, `convergence`, and `delivery` gates; retries, timeout recovery, and deterministic shards are attempts inside the owning gate and do not consume another epoch. Keep full-suite, build, integration, E2E, and visual gates in feature-level `validation`/task `verification`; put only cheap changed-scope checks safe to run for one Txx in that task's `task_checks`. Workers never inherit the heavy gates.
6. Run the CLI-owned **Deterministic Task-Graph Review**, including **User-Observable Path Coverage** and `real_entrypoint_evidence`, for coverage, dependency cycles, write-set safety, acceptance, and verification. Use agent review only when ambiguity or high-risk judgment remains; repair task-layer defects locally, or route upstream truth defects to their owner when changing the goal, confirmed scope, architecture, feasibility, or target boundary would be required.
7. Create the pointer-only implementation transition with `{{specify-subcmd:specify-runtime tasks handoff --feature-dir <feature-dir> --target implement --format json}}`, then use the shared `workflow complete-stage` gate as the single deterministic artifact validation. Repair or reopen the owning upstream phase on failure. Hand off directly to `{{invoke:implement}}` only after a clean result from that gate, a successful handoff receipt, and `next_command: /sp.implement`.

Do not edit production source or tests, migrations, or runtime configuration. This stage owns only the executable task graph and its task-generation evidence; implementation begins only in a separately invoked `{{invoke:implement}}` workflow.

## Detailed References

Read [Reference index](references/INDEX.md) before applying detailed contracts.

- [plan intake](references/plan-intake.md)
- [task generation sequence](references/task-generation-sequence.md)
- [task packet schema](references/task-packet-schema.md)
- [dependencies and parallel safety](references/dependencies-and-parallel-safety.md)
- [must preserve ledger](references/must-preserve-ledger.md)
- [review and repair](references/review-and-repair.md)
