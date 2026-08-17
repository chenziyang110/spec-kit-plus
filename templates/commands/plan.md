---
description: Use when the current specification package is ready for implementation planning and you need design artifacts before task breakdown or coding.
workflow_contract:
  when_to_use: The current spec package is ready for design work, but implementation should not start until explicit planning artifacts exist.
  primary_objective: Produce the planning artifact set that turns specification intent into an implementation-ready architecture and execution approach.
  primary_outputs: 'Canonical agent-only `plan-contract.json` plus project-facing `plan.md`; `research.md`, `quickstart.md`, `data-model.md`, and `contracts/` only when their triggers are present; planning lane records only when delegated lanes are used. When Deep Research exists, Plan verifies and binds the runtime-owned handoff before synthesis. `workflow-state.md` remains resume state rather than phase handoff truth.'
  default_handoff: '/sp.tasks for decomposition; /sp.test-design is an optional post-plan gate for a comprehensive Test Universe and material plan; /sp.checklist remains optional for requirements-quality review.'
handoffs:
  - label: Design Tests
    agent: sp.test-design
    prompt: Freeze the planned feature test universe, cases, materials, coverage, and gaps before task decomposition.
    send: false
  - label: Create Tasks
    agent: sp.tasks
    prompt: Break the plan into tasks
    send: true
  - label: Create Checklist
    agent: sp.checklist
    prompt: Create a checklist for the following domain...
scripts:
  sh: scripts/bash/setup-plan.sh --json
  ps: scripts/powershell/setup-plan.ps1 -Json
agent_scripts:
  sh: scripts/bash/update-agent-context.sh __AGENT__
  ps: scripts/powershell/update-agent-context.ps1 -AgentType __AGENT__
---

{{spec-kit-include: ../command-partials/plan/shell.md}}

{{spec-kit-include: ../command-partials/common/senior-consequence-analysis-gate.md}}

{{spec-kit-include: ../command-partials/common/agent-phase-handoff.md}}
{{spec-kit-include: ../command-partials/common/run-bootstrap.md}}

{{spec-kit-include: ../command-partials/common/planning-cognition.md}}

[AGENT] For project-cognition-backed semantic intake, routing, audit, resume, or final-claim gates, read `references/semantic-work-contract.md`.

{{spec-kit-include: ../command-partials/common/adaptive-execution.md}}

[AGENT] `sp-plan` continues the same run created for the feature. Confirm the same run with `specify-runtime run show`, then execute planning work only through `specify-runtime run supervise`.

## Read-Only Test Design Projection Gate

`plan-contract.json#/test_design_gate/decision` is exactly
`not_selected`, `selected`, or `required`. `not_selected` records why no Test
Design input is being consumed. `selected` or `required` may initially carry an
all-null `projection_binding` while production is pending; partial binding is
invalid. Only when Plan actually consumes a producer-built Plan projection must
the binding be complete and verified before reading any selected obligation,
case, data, coverage, gap, or audit ref:

`{{specify-subcmd:specify-runtime test-design projection-verify --feature-dir <feature-dir> --projection-ref <project-relative-ref> --expected-sha256 <sha256> --format json}}`

Omit `--feature-dir` only for an explicitly selected project-scope projection.
The verified projection is a typed pointer-only planning input. Plan consumes it
read-only and must not create, patch, replace, weaken, or copy the canonical Test
Design publication, projection, catalog, data manifest, coverage matrix, gaps,
or audit result. If Plan needs the projection to decide architecture, a missing
or stale binding routes to `{{invoke:test-design}}`; otherwise Plan may finish
with the all-null pending binding and route the producer next. Test Design does
not require Plan completion. A Plan binding records only Plan's actual
consumption, never Tasks authorization, and must not use the Plan contract as a
self-hashing basis. Build the Plan projection against the current immutable
upstream `spec-contract.json`; then record only the returned binding in
`plan-contract.json`. Tasks later requires its own verified projection, a fresh
feature `handoff-to-tasks.json`, and runtime-owned task-index binding. Plan
decisions do not become canonical Test Design truth.

## Main Flow

1. Resolve `FEATURE_DIR` without creating `plan.md`. Prefer the explicit feature argument; otherwise use the managed Run's `SPECIFY_RUN_SUBJECT_ID` only when `SPECIFY_RUN_MANAGED=1`, `SPECIFY_RUN_SUBJECT_TYPE=feature`, and the current directory equals `SPECIFY_RUN_WORKSPACE`. Fall back to the installed prerequisite helper's paths-only mode only when it returns one unambiguous feature. Never infer the feature from the Run's private Git ref. Enter `plan` with the deterministic `specify-runtime workflow transition` command and stop on exit `10`; do not edit source/runtime/test files.
2. Only after the transition succeeds, run `{SCRIPT}` to create the plan skeleton or report `STATUS=noop` without overwriting existing work.
3. Query canonical `spec-contract.json` first with `specify-runtime artifact show`, using JSON pointers for its context capsule, evidence refs, and `semantic_delta`; query other workflow artifacts only when a required reference or stale-evidence condition demands it.
4. Preserve complete-first scope: do not split confirmed scope into MVP, future-work slices, `v1/v2`, `P0/P1`, or a smaller delivery unless the user confirmed the deferral contract.
5. Resolve the feature directory to a project-relative output path. If no contract exists, scaffold canonical `plan-contract.json` with `{{specify-subcmd:specify-runtime artifact scaffold --kind plan-contract --path "<project-relative-feature-dir>/plan-contract.json"}}`; never pass an absolute `FEATURE_DIR`. On reruns, preserve the existing top-level or `plan/plan-contract.json` location. Fill contract decisions with leased JSON-pointer patches. Query the `{SCRIPT}`-created `plan.md` skeleton through `artifact show` and fill only named sections with leased `artifact patch --section`; never emit or resubmit the full stable template. When triggered, create `research.md` only with `specify-runtime artifact scaffold --kind research`, `data-model.md` only with `specify-runtime artifact scaffold --kind data-model`, and `quickstart.md` only with `specify-runtime artifact scaffold --kind quickstart`, then patch named semantic sections. Protocol-specific files under `contracts/` remain flexible and use the generic artifact CLI only when their documented trigger is present.
6. If `spec-contract.json#/feasibility_gate.decision` is `required`, verify the runtime-published handoff before planning consumes it with `specify-runtime deep-research verify-handoff --feature-dir <feature-dir> --handoff-ref <handoff-ref> --expected-sha256 <handoff-sha256> --format json`. Treat `deep-research.md` as the compatible projection only. Copy only the verified `decision`, `handoff_ref`, `handoff_sha256`, `source_spec_sha256`, `state_revision`, `claim_status`, and `handoff_ids` into `plan-contract.json#/deep_research_binding`; a verified `not_needed` claim still binds the handoff but carries no invented PH IDs. If the feasibility decision is `not_selected`, preserve the template's null `deep_research_binding`. Do not restate Deep Research findings from chat or the projection alone.
7. Use `choose_subagent_dispatch(command_name="plan", snapshot, workload_shape)` only for isolated planning lanes. When lanes are delegated, create an absent `planning/lane-manifest.json` with `specify-runtime artifact scaffold --kind planning-lane-manifest --path <feature-dir>/planning/lane-manifest.json`; on resume query it with `artifact show`. Replace the bounded `/lanes` array as a whole through a fresh leased JSON-pointer patch after each material join, and patch `/status` separately at closeout; do not emulate array append. Each lane returns one compact agent-only result inline through `specify-runtime result submit --command plan`, and the runtime alone materializes the result path. Do not duplicate events or submit the manifest wholesale.
8. Add `Implementation Constitution`, `Reference Fidelity Inputs`, `Feature UI Brief Adoption`, `Design Change Adoption` and token strategy, `Dispatch Compilation Hints`, `Review-Risk Notes`, and `Input Risks From Alignment` when their triggers are present. Preserve every `MP-*` must-preserve obligation and conflict rule, plus `ui-brief.md`, `Reference-Implementation`, and `visual_comparison_or_human_review` refs, rather than re-parsing or weakening upstream decisions.
   For UI work, preserve the current contract's work/surface/platform dimensions, direction
   theses and approved visual, reference intents, real content/image plans, and
   evidence triad exactly; carry verified cognition-selected UI routes in the
   compact plan context capsule for worker packet compilation.
9. Re-check constitution, complexity, risk, locked planning decisions, verified Deep Research binding traceability, and the `test_design_gate`. Deep Research `PH-###` items remain direct evidence refs queried through their registered artifact owner; planning must not restate them as unsupported prose, and it must fail closed when the verified handoff/source hash/revision/claim no longer matches the consumed `deep_research_binding` in `plan-contract.json`. Run `{AGENT_SCRIPT}` to refresh the generated Agent context, then use the shared `workflow complete-stage` gate as the single deterministic artifact validation and fail closed on an incomplete planning package. When the user requested comprehensive test design, a repository/feature risk review requires it, or test-material provenance is planning-critical, record `selected` or `required` and recommend the independent `{{invoke:test-design}}` producer; otherwise record `not_selected` and recommend `{{invoke:tasks}}` directly. The default formal path remains Plan -> optional Test Design -> Tasks, but Test Design itself does not depend on completed Plan state.

Do not create `tasks.md` or `task-index.json`; the separately invoked task workflow owns them. Do not edit production source, tests, migrations, or runtime configuration during planning.

## Detailed References

Read [Reference index](references/INDEX.md) before applying detailed contracts.

- [spec package intake](references/spec-package-intake.md)
- [research and design lanes](references/research-and-design-lanes.md)
- [data model contracts and quickstart](references/data-model-contracts-and-quickstart.md)
- [constitution risk and complexity](references/constitution-risk-and-complexity.md)
- [subagent dispatch](references/subagent-dispatch.md)
- [plan contract fields](references/plan-contract-fields.md)
