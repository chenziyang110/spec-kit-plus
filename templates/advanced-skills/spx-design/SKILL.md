---
name: spx-design
description: Lean design-system workflow for advanced coding models. Use for a new product UI, redesign, rebrand, shared visual language, or an audit/update of the root DESIGN.md contract.
---

# SPX Design

Read `references/project-learning.md` and apply its consume-capture policy.
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
`.specify/design/design-brief.md`, `.specify/design/previews/*.html`,
`.specify/design/previews/*.approval.json`,
`.specify/design/references.md`, `.specify/design/options.md`,
`.specify/design/design-system.json`, `.specify/design/review.md`, and stable design rules in
`.specify/memory/project-rules.md` when they truly become project defaults.

Compile `.specify/design/design-brief.md` from the installed
`design-brief-template.md`. Infer repository evidence first, then ask one
high-impact design question at a time when the answer can change hierarchy,
density, component anatomy, motion, responsive/accessibility behavior,
reference fidelity, or approval scope. Do not ask for a production framework
merely to shape a framework-neutral preview. Confirm subject, audience, single
job, modules, locales, modes, platforms/viewports, comparison content,
component/state coverage, meaningful motion and `prefers-reduced-motion`, and
Must Preserve / May Adapt / Must Not boundaries. Record confirmed choices as
stable `DS-<KIND>-NNN` decisions with source, status, affected surfaces, and
verification; the brief is the decision ledger, not a chat transcript.

When creating a new direction or replacing a bootstrap seed, scaffold
`.specify/design/previews/round-NN.html` from the installed
`design-preview-template.html`. Produce exactly three project-specific
directions in that one self-contained board. Hold content, component/state
coverage, and viewports constant so visual, density, and motion differences are
comparable. Use modern native HTML/CSS—custom properties, cascade layers,
fluid scales, container queries, and progressive view transitions—with only
bounded inline review logic and no framework, CDN, remote runtime dependency,
network call, persistence, analytics, or business behavior.

Replace all placeholders, set candidate status, configure the embedded
`spec-kit-design-preview-manifest-v1` to match the visible specimen, and run
`{{specify-subcmd:design preview-lint .specify/design/previews/round-NN.html --level ready}}`,
and inspect direction switching, keyboard operation, responsive widths, state
coverage, motion, and reduced motion in a real browser. Present the exact round
path, direction IDs, and tradeoffs. Treat a requested hybrid as a new
inspectable composition in the next round. Iterate new numbered rounds until
the user approves; do not overwrite prior rounds or treat criticism as
approval. Freeze the approved round with
`{{specify-subcmd:design approve .specify/design/previews/round-NN.html --direction <direction-id> --format json}}`
and record
`approved_visual_ref: .specify/design/previews/round-NN.html#<direction-id>` in
the brief, review, and `DESIGN.md` `approval.visual_refs`, together with the
returned review round, preview/manifest SHA-256 values, sidecar, and exact
decision IDs. An edited approved file or missing/stale sidecar is invalid.
Refinement that preserves an already approved direction needs no ceremonial
re-selection.

Create or revise root `DESIGN.md` from `assets/design-system.md`. Record only
decisions that constrain downstream UI work: principles, foundations, tokens,
component and interaction rules, responsive/accessibility behavior, reference
fidelity, and required visual evidence. Make exceptions explicit and
verifiable.

Set `design_system.status: approved`, record the selected direction and
product/repository source refs plus `approval.visual_refs`, review round,
preview/manifest SHA-256 values, and decision IDs. Replace every asset
placeholder, run `{{specify-subcmd:design lint --level ready}}`, then export the
deterministic implementation contract with
`{{specify-subcmd:design export DESIGN.md --format json --out .specify/design/design-system.json}}`.
Do not hand off a structurally valid but generic or unapproved seed.

Write `.specify/design/review.md` with the mode, inputs, approved direction,
visual reference, hashes, decision IDs, covered platforms, risks, lint/export
results, and one recommended next workflow. Ask the user to review the written
`DESIGN.md` before recording the final design handoff; approval of an earlier
direction artifact does not silently approve a drifted final contract.

This workflow owns the design-system contract, not production implementation.
Do not edit application source, tests, or generated component code. Preserve
useful existing decisions and validate that referenced tokens/components exist
or are clearly marked planned. Continue feature-specific requirements through
`$spx-specify` and implementation design/tasks through `$spx-plan` as explicit
handoffs. The project-level preview owns reusable design decisions; the later
feature-level `ui-target.html` owns one feature's concrete composition. This
invocation authorizes only this workflow stage; do not invoke another workflow
in this run.
