---
name: spx-design
description: Lean design-system workflow for advanced coding models. Use for a new product UI, redesign, rebrand, shared visual language, or an audit/update of the root DESIGN.md contract.
---

# SPX Design

Read `references/project-cognition.md`, using cognition intent `plan`, and
`references/design-contract.md`. Read `references/ui-quality-gate.md`. Read
`references/consequence-gate.md` when
shared component state or generated consumers change.

Inspect the current root `DESIGN.md`, relevant live UI entry points, existing
tokens/components, accessibility rules, and supplied references. Distinguish
observed product language from new design decisions; do not invent a parallel
system when an established one can be extended.

Create or resume `.specify/design/design-state.md` before synthesis and reread
it after interruption or compaction. Persist `active_command: sp-design`,
`phase_mode: design-only`, current stage, selected mode/direction, approval
state, lint result, next action, and next command. The `allowed_writes` are only
`DESIGN.md`, `.specify/design/design-state.md`,
`.specify/design/references.md`, `.specify/design/options.md`,
`.specify/design/review.md`, and stable design rules in
`.specify/memory/project-rules.md` when they truly become project defaults.

When creating a new direction or replacing a bootstrap seed, present two or
three project-specific directions grounded in subject, audience, and one user
job. Each states visual/content/interaction theses, a signature element, and
creative-risk tradeoffs, and has an inspectable visual artifact. Obtain user
approval of that artifact before locking one. Refinement that preserves an
already approved direction needs no ceremonial re-selection.

Create or revise root `DESIGN.md` from `assets/design-system.md`. Record only
decisions that constrain downstream UI work: principles, foundations, tokens,
component and interaction rules, responsive/accessibility behavior, reference
fidelity, and required visual evidence. Make exceptions explicit and
verifiable.

Set `design_system.status: approved`, record the selected direction and
product/repository source refs plus `approval.visual_refs`, replace every asset placeholder, and run
`{{specify-subcmd:design lint --level ready}}`. Do not hand off a structurally valid but
generic or unapproved seed.

Write `.specify/design/review.md` with the mode, inputs, approved direction and
visual reference, covered platforms, risks, lint result, and one recommended
next workflow. Ask the user to review the written `DESIGN.md` before recording
the final design handoff; approval of an earlier direction artifact does not
silently approve a drifted final contract.

This workflow owns the design-system contract, not production implementation.
Do not edit application source, tests, or generated component code. Preserve
useful existing decisions and validate that referenced tokens/components exist
or are clearly marked planned. Continue feature-specific requirements through
`$spx-specify` and implementation design/tasks through `$spx-plan` as explicit
handoffs. This invocation authorizes only this workflow stage; do not invoke
another workflow in this run.
