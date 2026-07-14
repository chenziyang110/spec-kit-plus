---
name: spx-design
description: Lean design-system workflow for advanced coding models. Use for a new product UI, redesign, rebrand, shared visual language, or an audit/update of the root DESIGN.md contract.
---

# SPX Design

Read `references/project-cognition.md`, using cognition intent `plan`, and
`references/design-contract.md`. Read `references/consequence-gate.md` when
shared component state or generated consumers change.

Inspect the current root `DESIGN.md`, relevant live UI entry points, existing
tokens/components, accessibility rules, and supplied references. Distinguish
observed product language from new design decisions; do not invent a parallel
system when an established one can be extended.

Create or revise root `DESIGN.md` from `assets/design-system.md`. Record only
decisions that constrain downstream UI work: principles, foundations, tokens,
component and interaction rules, responsive/accessibility behavior, reference
fidelity, and required visual evidence. Make exceptions explicit and
verifiable.

This workflow owns the design-system contract, not production implementation.
Do not edit application source, tests, or generated component code. Preserve
useful existing decisions and validate that referenced tokens/components exist
or are clearly marked planned. Continue feature-specific requirements through
`$spx-specify` and implementation design/tasks through `$spx-plan`.
