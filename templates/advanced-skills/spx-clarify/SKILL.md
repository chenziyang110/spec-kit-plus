---
name: spx-clarify
description: Existing-spec repair workflow for advanced coding models. Use when a specification package has planning-critical ambiguity, weak acceptance, contradictions, or new constraints that should be absorbed without recreating the feature.
---

# SPX Clarify

Read `references/project-cognition.md`, using cognition intent `plan`,
`references/clarification-contract.md`, and `references/consequence-gate.md`
only on its triggers.

Resolve the existing feature with the installed prerequisite script in
paths-only mode. Do not create a new feature. Read `spec-contract.json` first,
then only the views, discussion handoff, UI evidence, project rules, or live
paths needed for the named gaps.

Identify decisions whose alternatives materially change behavior, acceptance,
interfaces, lifecycle, security, compatibility, or scope. Resolve repository
facts from evidence. Ask the user only for product decisions the repository
cannot own, in a small prioritized batch. Preserve confirmed scope and record
safe assumptions explicitly.

Apply accepted answers to the authoritative spec contract and its referenced
views; update existing workflow state and clarification evidence only when they
are already part of the feature package. Validate the result and ensure every
planning blocker is resolved, explicitly retained, or routed to
`$spx-deep-research`.

Do not plan or implement. Continue to `$spx-plan` only when the strengthened
package is planning-ready; otherwise report the exact unresolved decision and
why it blocks.
