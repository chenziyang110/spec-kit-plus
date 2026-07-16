---
name: spx-clarify
description: Existing-spec repair workflow for advanced coding models. Use when a specification package has planning-critical ambiguity, weak acceptance, contradictions, or new constraints that should be absorbed without recreating the feature.
---

# SPX Clarify

Read `references/project-learning.md` and apply its consume-capture policy.
Read `references/project-cognition.md`, using cognition intent `plan`,
`references/clarification-contract.md`, and `references/consequence-gate.md`
only on its triggers.
Read `references/ui-quality-gate.md` when the planning blocker concerns UI
experience, design readiness, states, responsive behavior, or fidelity.

Resolve the existing feature with the installed prerequisite script in
paths-only mode. Do not create a new feature. Read `spec-contract.json` first,
then only the views, discussion handoff, UI evidence, project rules, or live
paths needed for the named gaps.

Create or resume runtime-owned `workflow-state.md` before substantive work,
using the installed workflow-state template only when it is absent. Record
`active_command: sp-clarify`, `phase_mode: planning-only`, the source revision,
target boundary, current blocker, and next route without copying spec truth.
Run `{{specify-subcmd:hook validate-state --command clarify --feature-dir <feature-dir> --autofix --format json}}`
and fail closed if the repaired state still does not validate.

Identify decisions whose alternatives materially change behavior, acceptance,
interfaces, lifecycle, security, compatibility, or scope. Resolve repository
facts from evidence. Ask the user only for product decisions the repository
cannot own, in a small prioritized batch. Preserve confirmed scope and record
safe assumptions explicitly.

Apply accepted answers to the authoritative spec contract and its referenced
views. The complete clarification working set is `spec.md`, `alignment.md`,
`context.md`, `references.md`, `workflow-state.md`,
`clarification/handoffs/`, `clarification/evidence-index.json`, and
`clarification/checkpoints.ndjson`; initialize missing clarification evidence
surfaces, preserve existing records, and consume every accepted handoff into a
named artifact section, explicit deferral, or blocker. Ensure every planning
blocker is resolved, explicitly retained, or routed to `$spx-deep-research`.

Run
`{{specify-subcmd:hook validate-artifacts --command clarify --feature-dir <feature-dir> --format json}}`
before reporting planning readiness. Repair owned artifacts or fail closed on a
non-OK result.

This invocation authorizes only this workflow stage. Do not plan or implement.
Do not invoke `$spx-deep-research`. Do not invoke `$spx-plan`. Report the
applicable workflow as the next handoff when the package needs research or
becomes planning-ready; otherwise report the exact unresolved decision and why
it blocks.
