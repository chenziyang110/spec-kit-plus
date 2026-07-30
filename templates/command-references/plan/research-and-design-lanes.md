Trigger: when planning needs research, design-system/UI adoption, operational consequence design, capability mapping, or delegated design lanes.

Purpose: resolve implementation-shaping uncertainty while preserving confirmed scope and reusing upstream evidence.

Preserved Contract: planning may refine implementation design but cannot silently reduce scope, drop protected behavior, or substitute unsupported assumptions for evidence.

## Complete-First Scope Preservation

Treat `spec-contract.json` as authoritative for confirmed delivery scope and deferrals. `plan-contract.json` owns the versioned complete-first policy; downstream artifacts reference it instead of copying the policy body.

- Plan the complete user-confirmed scope. Complexity alone is not a valid reason to shrink scope or invent `v1/v2`, `P0/P1`, or a future-work delivery slice; it changes decomposition, ordering, validation, and dispatch.
- A deferral requires explicit user confirmation with confirmation source, exact excluded behavior, residual risk, reopen or stop condition, and downstream artifact.
- If the user did not confirm the deferral, design the behavior, create a refinement or validation checkpoint, or return a truthful blocker.

## Context Capsule Intake

Reuse `spec-contract.json.context_capsule`. Run one additional bounded project cognition intake only when a planning facet is missing or its stale condition is true. Carry new evidence back into the plan contract; do not create a second broad repository summary.

Query project-facing `spec.md` and alignment/context views through targeted `specify-runtime artifact show` calls only for a named required ref or evidence gap.

## Conditional Research

Research only questions that can change architecture, dependency choice, compatibility, security, data shape, external integration, or validation. Prefer live repository evidence and primary sources. Record decision, rationale, rejected alternative only when it can reappear, confidence, and implementation proof.

When `research.md` is triggered, create it with `specify-runtime artifact scaffold --kind research --path <feature-dir>/research.md`, then fill only the relevant named sections through leased `artifact patch` calls. The runtime expands `research-template.md`; never read and reproduce its stable structure in memory. Prefer official documentation, standards, and primary sources; treat model memory as provisional. Research must reduce planning ambiguity rather than accumulate background reading, and every recommendation names confidence, assumptions, validation, environment/dependency notes, and why hand-rolling is or is not justified.

If no such unknown exists, record `research_status: not-needed` in `plan-contract.json` and do not generate `research.md`.

## Design And UI Inputs

For UI-facing work, query `DESIGN.md`, `ui-brief.md`, and the approved immutable design handoff through targeted `specify-runtime artifact show` calls; consume the returned contracts and fidelity refs only when selected by the spec contract. Record Feature UI Brief Adoption and Design System Adoption, including token strategy. Preserve the exact preview/manifest/handoff digests, immutable handoff ref, selected `DS-*` and `DH-*` IDs, `Reference-Implementation`, tokens, component ownership, required states, accessibility, fidelity criteria, allowed adaptation, forbidden drift, `visual_comparison_or_human_review`, Playwright screenshots or representative output when applicable, real-entrypoint evidence, and accepted deviations. Select structured handoff rows by ID; never recreate their values from prose.

Do not repeat UI reference parsing already completed upstream unless the source changed or a required implementation facet is missing.

## Operational Consequence Design

For each task-relevant `CA-###` ref, add phase-owned operational decisions: state behavior, ordering/concurrency, dependency impact, recovery, observability, migration/rollout when relevant, validation, and stop/reopen condition. Do not copy the complete upstream affected-object analysis.

If a consequence cannot be designed safely, stop before tasks and route to the owning requirement, clarification, or research phase.

## Capability Preservation

Map each preserved operation-shaped capability to an explicit entry point, owning surface, validation proof, and task interface. A template or documentation note is not a replacement for a confirmed create/scaffold/authoring operation unless the user confirmed that behavior.

Command-surface minimization uses entry-point remapping; it must not delete capability. Preserve the operation through an explicit TUI route, core API, CLI, or another confirmed executable surface.

## Adaptive Planning Lanes

- `light`: leader-inline synthesis; no lane files.
- `standard`: delegate only isolated research, data-model, contract, or validation-scenario work when expected critical-path gain exceeds handoff cost.
- `heavy`: use validated result-channel lanes when risk or independent expertise requires them; block if safe packetization is unavailable.

When lanes are delegated, create an absent `planning/lane-manifest.json` with `specify-runtime artifact scaffold --kind planning-lane-manifest --path <feature-dir>/planning/lane-manifest.json`; query it on resume. Replace the bounded `/lanes` array as a whole through a fresh leased JSON-pointer patch at material joins and patch `/status` separately at closeout; the patch API does not append inside arrays. Submit each lane result inline through `specify-runtime result submit --command plan`. Never submit the manifest wholesale. Do not require separate evidence-index and checkpoint logs for the same event.

Before finalizing, ensure every accepted lane result is integrated, deferred with valid confirmation, or blocked with recovery.
