---
name: spx-clarify
description: Existing-spec repair workflow for advanced coding models. Use when a specification package has planning-critical ambiguity, weak acceptance, contradictions, or new constraints that should be absorbed without recreating the feature.
---

# SPX Clarify

Read `references/project-learning.md` and apply its consume-capture policy.
Read `references/native-subagents.md` when clarification lanes are delegated.
Read `references/project-cognition.md`, using cognition intent `plan`,
`references/clarification-contract.md`, and `references/consequence-gate.md`
only on its triggers.
Read `references/ui-quality-gate.md` when the planning blocker concerns UI
experience, design readiness, states, responsive behavior, or fidelity.

Resolve the existing feature with the installed prerequisite script in
paths-only mode. Do not create a new feature. Query `spec-contract.json` first through `specify-runtime artifact show`,
then only the views, discussion handoff, UI evidence, project rules, or live
paths needed for the named gaps.

Before any write, run
`{{specify-subcmd:specify-runtime workflow show --feature-dir <feature-dir> --format json}}`.
`FEATURE_DIR/workflow.json` is CLI-owned; this auxiliary skill must not write
it, and its expected required-stage owner is `specify`. On missing, corrupt,
different, or completed runtime state, stop with the returned blocker or a
typed owner handoff containing the observed stage, expected owner, affected
files, exact next action, unblock criteria, and resume argv. Never overwrite
either state surface to force entry.

Create initial `workflow-state.md` through `specify-runtime artifact scaffold --kind workflow-state`; resume and mutate it only through targeted `artifact show` and leased `artifact patch` before substantive
work. The runtime expands the installed template; never read and reproduce its
stable skeleton. Record
`active_command: sp-clarify`, `phase_mode: planning-only`, the source revision,
target boundary, current blocker, and next route without copying spec truth.
Run `{{specify-subcmd:specify-runtime hook validate-state --command clarify --feature-dir <feature-dir> --autofix --format json}}`
and fail closed if the repaired state still does not validate.

Recover a missing fixed spec-package view only through
`specify-runtime artifact scaffold --kind alignment`, `specify-runtime artifact
scaffold --kind specify-context`, or `specify-runtime artifact scaffold --kind
references`; query existing views and patch named sections instead of replacing
them. Before the first durable clarification event, create absent
`clarification/evidence-index.json` with `specify-runtime artifact scaffold
--kind clarification-evidence-index` and `clarification/checkpoints.ndjson` with
`specify-runtime artifact scaffold --kind clarification-checkpoints`. Replace
the bounded `/lanes` array through a fresh
JSON-pointer patch at material joins and append each checkpoint only through
`artifact patch --append-json`. Lane handoffs are materialized only by `result
submit --command clarify`; never generically submit or directly create any of
these state files.

Identify decisions whose alternatives materially change behavior, acceptance,
interfaces, lifecycle, security, compatibility, or scope. Resolve repository
facts from evidence. Ask the user only for product decisions the repository
cannot own, in a small prioritized batch. Preserve confirmed scope and record
safe assumptions explicitly.

Apply accepted answers to the authoritative spec contract and its referenced
views. The complete clarification working set is `spec.md`, `alignment.md`,
`context.md`, `references.md`, `workflow-state.md`,
`clarification/handoffs/`, `clarification/evidence-index.json`, and
`clarification/checkpoints.ndjson`; query them through `artifact show`, create
or mutate them only through their registered runtime owner and a granted
lease, preserve existing records, and consume every accepted handoff into a
named artifact section, explicit deferral, or blocker. Ensure every planning
blocker is resolved, explicitly retained, or routed to `$spx-deep-research`.

Run
`{{specify-subcmd:specify-runtime hook validate-artifacts --command clarify --feature-dir <feature-dir> --format json}}`
before reporting planning readiness. Repair owned artifacts or fail closed on a
non-OK result.

This invocation authorizes only this workflow stage. Do not plan or implement.
Do not invoke `$spx-deep-research`. Do not invoke `$spx-plan`. Report the
applicable workflow as the next handoff when the package needs research or
becomes planning-ready; otherwise report the exact unresolved decision and why
it blocks.
