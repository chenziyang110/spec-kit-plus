---
description: Use when a new or changed feature request needs guided requirement discovery and a planning-ready specification package.
workflow_contract:
  when_to_use: A new or changed feature request needs a planning-ready specification package instead of immediate implementation.
  primary_objective: 'Produce a planning-ready specification contract through discovery for raw requests or semantic-delta compilation for a confirmed discussion contract, followed by deterministic completeness and traceability review.'
  primary_outputs: 'Canonical agent-only `FEATURE_DIR/spec-contract.json` plus human/project `FEATURE_DIR/spec.md`; `alignment.md`, `context.md`, `references.md`, and a requirements report only when their triggered content has independent value; `workflow-state.md` remains resume state rather than a handoff.'
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

1. Resolve discussion handoff intake before feature creation; require canonical agent-only `handoff-to-specify.json`, verify `handoff-ready`, `quality_gate.status: user_confirmed`, and `planning_gate_status: ready`, derive the feature description, and do not pass the raw contract path as the feature description. Do not use `specification-input.md`, `discussion-state.md`, or other discussion source files as a substitute.
2. Verify the installed command surface with `specify --help`, then run `{SCRIPT}` from the repo root as the generated create-feature script; generated projects resolve this to `.specify/scripts/bash/create-new-feature.sh "$ARGUMENTS"` or `.specify/scripts/powershell/create-new-feature.ps1 "$ARGUMENTS"`. If the feature-creation script exits non-zero, stop with its evidence; do not call `specify lane register` or invent a feature-creation CLI command.
3. Explore project context with project cognition as advisory navigation, then prove current facts from live files and record source evidence.
4. Select discovery mode for a raw request or compile mode for a confirmed discussion contract. In compile mode, compute `semantic_delta`, ask only about a planning-critical delta, and do not repeat user review when `semantic_delta` is empty.
5. Decompose semantic terms into explicit decisions and capability operations in `spec-contract.json`; present two or three approaches only when behavior, boundary, compatibility, or acceptance proof changes.
6. Preserve the discussion contract by reference. Read discussion source files only when a named evidence reference is stale, missing, or contradictory; carry its existing decision digest instead of rebuilding it.
7. For UI-facing work, read selected `DESIGN.md` and UI refs; compile `Experience Requirements`, design-system readiness (`design_system_status`, `design_risk_level`), and `ui-brief.md`/`Reference-Implementation` fidelity evidence. Treat a missing required system as a strong blocker and a non-blocking adoption gap as a soft risk. Handle raw UI reference input through `choose_ui_reference_lane_dispatch` and `ui-reference-artifact`.
8. Write `spec-contract.json`, render or update project-facing artifacts, and run deterministic completeness, traceability, and contradiction checks. Request user review only for non-empty semantic delta or a real unresolved decision, then recommend exactly one next command: `/sp.plan`, `/sp.clarify`, or `/sp.deep-research`.

## Detailed References

Read [Reference index](references/INDEX.md) before applying detailed contracts.

- [discussion handoff validation](references/discussion-handoff-validation.md)
- [semantic traceability](references/semantic-traceability.md)
- [ui reference lane](references/ui-reference-lane.md)
- [artifact package](references/artifact-package.md)
- [question cadence and review](references/question-cadence-and-review.md)
- [self review and quality gates](references/self-review-and-quality-gates.md)
