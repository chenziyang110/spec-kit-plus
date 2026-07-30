---
description: Use when a new or changed feature request needs the artifact CLI for guided discovery and a planning-ready specification package.
workflow_contract:
  when_to_use: A new or changed feature request needs a planning-ready specification package instead of immediate implementation.
  primary_objective: 'Produce and patch the planning-ready specification contract only through `specify-runtime artifact`, followed by deterministic completeness and traceability review.'
  primary_outputs: 'CLI-owned `spec-contract.json`, `spec.md`, triggered views, and `workflow-state.md`, created or changed only through `specify-runtime artifact`.'
  default_handoff: 'After user review, recommend exactly one next command: `/sp.plan`, `/sp.clarify`, or `/sp.deep-research`.'
handoffs:
  - label: Build Technical Plan
    agent: sp.plan
    prompt: Create a plan for the spec. I am building with...
  - label: Prove Feasibility Before Plan
    agent: sp.deep-research
    prompt: Prove the unverified implementation-chain risks recorded by sp-specify, then hand findings and demo evidence to sp-plan.
    send: true
scripts:
  sh: scripts/bash/create-new-feature.sh "{ARGS}"
  ps: scripts/powershell/create-new-feature.ps1 "{ARGS}"
---

{{spec-kit-include: ../command-partials/specify/shell.md}}

{{spec-kit-include: ../command-partials/common/senior-consequence-analysis-gate.md}}

{{spec-kit-include: ../command-partials/common/agent-phase-handoff.md}}

{{spec-kit-include: ../command-partials/common/planning-cognition.md}}

[AGENT] For project-cognition-backed semantic intake, routing, audit, resume, or final-claim gates, read `references/semantic-work-contract.md`.

{{spec-kit-include: ../command-partials/common/read-only-evidence-lanes.md}}

## Main Flow

1. Resolve discussion handoff intake before feature creation through `specify-runtime discussion list|status|validate-handoff` plus targeted `artifact show`; require canonical agent-only `handoff-to-specify.json`, verify `handoff-ready`, `quality_gate.status: user_confirmed`, and `planning_gate_status: ready`, derive the feature description, and do not pass the raw contract path as the feature description. Do not use `specification-input.md`, `discussion-state.md`, or other discussion source files as a substitute.
2. Verify the installed runtime surface with `{{specify-subcmd:specify-runtime api list --format json}}`, then run `{SCRIPT}` from the repo root as the generated create-feature script; generated projects resolve this to `.specify/scripts/bash/create-new-feature.sh "$ARGUMENTS"` or `.specify/scripts/powershell/create-new-feature.ps1 "$ARGUMENTS"`. If the feature-creation script exits non-zero, stop with its evidence; do not call an invented feature-creation CLI command. After it returns `FEATURE_DIR`, enter or resume `specify` through the deterministic workflow runtime before writing any feature artifact.
3. Explore project context with project cognition as advisory navigation, then prove current facts from live files and record source evidence.
4. Select discovery mode for a raw request or compile mode for a confirmed discussion contract. In compile mode, compute `semantic_delta`, ask only about a planning-critical delta, and do not repeat user review when `semantic_delta` is empty.
5. Decompose semantic terms into explicit decisions and capability operations in `spec-contract.json`. Build `acceptance_coverage` as one stable `requirement_ref`/`acceptance_ref` pair per row: cover every `scope.in` and `capability_operations` JSON Pointer, map every acceptance criterion exactly once, and never use one criterion as the closure proof for multiple independent requirements. Present two or three approaches only when behavior, boundary, compatibility, or acceptance proof changes.
6. Preserve the discussion contract by reference. Query supporting discussion artifacts through their artifact/evidence CLI owner only when a named evidence reference is stale, missing, or contradictory; carry its existing decision digest instead of rebuilding it.
7. For UI-facing work—with or without supplied screenshots—query selected
   `DESIGN.md` through `specify-runtime artifact show` and live UI evidence through its evidence owner; compile `Experience Requirements`,
   design-system readiness (`design_system_status`, `design_risk_level`), and a
   feature `ui-brief.md` via `specify-runtime artifact scaffold --kind ui-brief` plus leased `artifact patch` calls, and the complete current `design_contract` for
   substantive UI changes. Separately patch work type, surface type, platform,
   subject, audience, single job, visual/content/interaction theses, signature,
   approved visual ref, reference intents, real content/image plans, and the
   structure/visual/runtime evidence triad through the artifact/evidence CLIs. Treat a bootstrap or
   missing required system as a strong blocker and a non-blocking adoption gap
   as a soft risk. When raw UI references exist, additionally use
   `choose_ui_reference_lane_dispatch`, `ui-reference-artifact`, and
   `Reference-Implementation` fidelity evidence.
8. Create `spec-contract.json` with `artifact scaffold --kind spec-contract`, then fill only targeted JSON pointers through leased `artifact patch`. Query the prerequisite-script-created `spec.md` skeleton through `artifact show` and fill named sections through leased `artifact patch --section`; never emit or resubmit the stable template. Route every conditional project-facing artifact through its registered CLI owner. Never write canonical files directly or stage temporary payload files. Run deterministic validation and fail closed if incomplete.

Create only specification-stage outputs. Do not create `plan-contract.json`, `plan.md`, research/design-plan artifacts, `tasks.md`, or `task-index.json`; the separately invoked planning and task workflows own them. Do not edit production source, tests, migrations, or runtime configuration.

## Detailed References

Read [Reference index](references/INDEX.md) before applying detailed contracts.

- [discussion handoff validation](references/discussion-handoff-validation.md)
- [semantic traceability](references/semantic-traceability.md)
- [ui reference lane](references/ui-reference-lane.md)
- [artifact package](references/artifact-package.md)
- [question cadence and review](references/question-cadence-and-review.md)
- [self review and quality gates](references/self-review-and-quality-gates.md)
