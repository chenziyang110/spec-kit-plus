---
description: Use when the current specification package is ready for implementation planning and you need design artifacts before task breakdown or coding.
workflow_contract:
  when_to_use: The current spec package is ready for design work, but implementation should not start until explicit planning artifacts exist.
  primary_objective: Produce the planning artifact set that turns specification intent into an implementation-ready architecture and execution approach.
  primary_outputs: 'Canonical agent-only `plan-contract.json` plus project-facing `plan.md`; `research.md`, `quickstart.md`, `data-model.md`, and `contracts/` only when their triggers are present; planning lane records only when delegated lanes are used. `workflow-state.md` remains resume state rather than phase handoff truth.'
  default_handoff: '/sp.tasks for decomposition; /sp.checklist remains optional for requirements-quality review, not a default handoff.'
handoffs:
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

## Main Flow

1. Resolve `FEATURE_DIR` without creating `plan.md`. Prefer the explicit feature argument; otherwise use the managed Run's `SPECIFY_RUN_SUBJECT_ID` only when `SPECIFY_RUN_MANAGED=1`, `SPECIFY_RUN_SUBJECT_TYPE=feature`, and the current directory equals `SPECIFY_RUN_WORKSPACE`. Fall back to the installed prerequisite helper's paths-only mode only when it returns one unambiguous feature. Never infer the feature from the Run's private Git ref. Enter `plan` with the deterministic `specify-runtime workflow transition` command and stop on exit `10`; do not edit source/runtime/test files.
2. Only after the transition succeeds, run `{SCRIPT}` to create the plan skeleton or report `STATUS=noop` without overwriting existing work.
3. Query canonical `spec-contract.json` first with `specify-runtime artifact show`, using JSON pointers for its context capsule, evidence refs, and `semantic_delta`; query other workflow artifacts only when a required reference or stale-evidence condition demands it.
4. Preserve complete-first scope: do not split confirmed scope into MVP, future-work slices, `v1/v2`, `P0/P1`, or a smaller delivery unless the user confirmed the deferral contract.
5. Resolve the feature directory to a project-relative output path. If no contract exists, scaffold canonical `plan-contract.json` with `{{specify-subcmd:specify-runtime artifact scaffold --kind plan-contract --path "<project-relative-feature-dir>/plan-contract.json"}}`; never pass an absolute `FEATURE_DIR`. On reruns, preserve the existing top-level or `plan/plan-contract.json` location. Fill contract decisions with leased JSON-pointer patches. Query the `{SCRIPT}`-created `plan.md` skeleton through `artifact show` and fill only named sections with leased `artifact patch --section`; never emit or resubmit the full stable template. When triggered, create `research.md` only with `specify-runtime artifact scaffold --kind research`, `data-model.md` only with `specify-runtime artifact scaffold --kind data-model`, and `quickstart.md` only with `specify-runtime artifact scaffold --kind quickstart`, then patch named semantic sections. Protocol-specific files under `contracts/` remain flexible and use the generic artifact CLI only when their documented trigger is present.
6. Use `choose_subagent_dispatch(command_name="plan", snapshot, workload_shape)` only for isolated planning lanes. When lanes are delegated, create an absent `planning/lane-manifest.json` with `specify-runtime artifact scaffold --kind planning-lane-manifest --path <feature-dir>/planning/lane-manifest.json`; on resume query it with `artifact show`. Replace the bounded `/lanes` array as a whole through a fresh leased JSON-pointer patch after each material join, and patch `/status` separately at closeout; do not emulate array append. Each lane returns one compact agent-only result inline through `specify-runtime result submit --command plan`, and the runtime alone materializes the result path. Do not duplicate events or submit the manifest wholesale.
7. Add `Implementation Constitution`, `Reference Fidelity Inputs`, `Feature UI Brief Adoption`, `Design System Adoption` and token strategy, `Dispatch Compilation Hints`, `Review-Risk Notes`, and `Input Risks From Alignment` when their triggers are present. Preserve every `MP-*` must-preserve obligation and conflict rule, plus `ui-brief.md`, `Reference-Implementation`, and `visual_comparison_or_human_review` refs, rather than re-parsing or weakening upstream decisions.
   For UI work, preserve the current contract's work/surface/platform dimensions, direction
   theses and approved visual, reference intents, real content/image plans, and
   evidence triad exactly; carry verified cognition-selected UI routes in the
   compact plan context capsule for worker packet compilation.
8. Re-check constitution, complexity, risk, locked planning decisions, and deep-research `PH-###` traceability. Deep-research `PH-###` items remain direct evidence refs queried through their registered artifact owner; planning must not restate them as unsupported prose. Run `{AGENT_SCRIPT}` to refresh the generated Agent context, then use the shared `workflow complete-stage` gate as the single deterministic artifact validation and fail closed on an incomplete planning package before recommending `{{invoke:tasks}}`.

Do not create `tasks.md` or `task-index.json`; the separately invoked task workflow owns them. Do not edit production source, tests, migrations, or runtime configuration during planning.

## Detailed References

Read [Reference index](references/INDEX.md) before applying detailed contracts.

- [spec package intake](references/spec-package-intake.md)
- [research and design lanes](references/research-and-design-lanes.md)
- [data model contracts and quickstart](references/data-model-contracts-and-quickstart.md)
- [constitution risk and complexity](references/constitution-risk-and-complexity.md)
- [subagent dispatch](references/subagent-dispatch.md)
- [plan contract fields](references/plan-contract-fields.md)
