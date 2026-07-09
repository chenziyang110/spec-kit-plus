---
description: Use when a new or changed feature request needs guided requirement discovery and a planning-ready specification package.
workflow_contract:
  when_to_use: A new or changed feature request needs a planning-ready specification package instead of immediate implementation.
  primary_objective: 'Produce a reviewed, planning-ready specification package through context exploration, one-question-at-a-time clarification, approach comparison, semantic term decomposition, artifact self-review, and user review.'
  primary_outputs: '`FEATURE_DIR/spec.md`, `FEATURE_DIR/alignment.md`, `FEATURE_DIR/context.md`, `FEATURE_DIR/references.md` when useful, `FEATURE_DIR/workflow-state.md`, `FEATURE_DIR/checklists/requirements.md`, and the minimal compatibility handoff `FEATURE_DIR/brainstorming/handoff-to-specify.json`.'
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

[AGENT] For project-cognition-backed semantic intake, routing, audit, resume, or final-claim gates, read `references/semantic-work-contract.md`.

{{spec-kit-include: ../command-partials/common/read-only-evidence-lanes.md}}

## Main Flow

1. Resolve discussion handoff intake before feature creation; require both `handoff-to-specify.md` and `handoff-to-specify.json`, verify `handoff-ready`, `quality_gate.status: user_confirmed`, and `planning_gate_status: ready`, derive the feature description, and do not pass the raw handoff path as the feature description. Do not use `specification-input.md`, `discussion-state.md`, or other discussion source files as a substitute for the ready handoff pair.
2. Run `{SCRIPT}` from the repository root to create or resume the feature workspace; generated projects resolve this to `.specify/scripts/bash/create-new-feature.sh "$ARGUMENTS"` or `.specify/scripts/powershell/create-new-feature.ps1 "$ARGUMENTS"`.
3. Explore project context with project cognition as advisory navigation, then prove current facts from live files and record source evidence.
4. Ask one high-impact question at a time only for planning-critical ambiguity; otherwise continue with the safe recommended/default path.
5. Decompose semantic terms, preserve `source_signal_disposition`, and present two or three approaches or `2-3 approaches` when behavior, boundary, compatibility, or acceptance proof changes.
6. Preserve discussion source files including `discussion-log.md`, `requirements.md`, and `open-questions.md`; build the `Discussion Decision Digest` and `discussion_decision_digest` instead of flattening upstream intent.
7. Handle UI reference input through `choose_ui_reference_lane_dispatch`, `ui-reference-artifact`, `ui-reference-notes.md`, `ui-brief.md`, and `Reference-Implementation` fidelity evidence rules.
8. Write and self-review the artifact package, then ask for user review. Recommend exactly one next command: `/sp.plan`, `/sp.clarify`, or `/sp.deep-research`.

## Detailed References

Read [Reference index](references/INDEX.md) before applying detailed contracts.

- [discussion handoff validation](references/discussion-handoff-validation.md)
- [semantic traceability](references/semantic-traceability.md)
- [ui reference lane](references/ui-reference-lane.md)
- [artifact package](references/artifact-package.md)
- [question cadence and review](references/question-cadence-and-review.md)
- [self review and quality gates](references/self-review-and-quality-gates.md)
