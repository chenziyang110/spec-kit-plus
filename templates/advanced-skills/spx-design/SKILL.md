---
name: spx-design
description: Lean design-system workflow for advanced coding models covering new product UI, redesign, rebrand, shared visual language, and root DESIGN.md contract maintenance through the design CLI.
---

# SPX Design

Read `references/project-learning.md` and apply its consume-capture policy.
Read `references/project-cognition.md`, using cognition intent `plan`, and
`references/design-contract.md`. Read `references/ui-quality-gate.md`. Read
`references/consequence-gate.md` when
shared component state or generated consumers change.

Query the current root `DESIGN.md` through `specify-runtime artifact show`, then inspect relevant live UI entry points, existing
tokens/components, accessibility rules, and supplied references. Distinguish
observed product language from new design decisions; do not invent a parallel
system when an established one can be extended.

Initialize `.specify/design/design-state.md` through `specify-runtime design preview`, resume it through `artifact show`, and query
it after interruption or compaction. Persist `active_command: sp-design`,
`phase_mode: design-only`, current stage, selected mode/direction, approval
state, lint result, next action, and next command. The `allowed_writes` are only
`DESIGN.md`, `.specify/design/design-state.md`,
`.specify/design/design-brief.md`, `.specify/design/previews/*.html`,
`.specify/design/previews/*.approval.json`,
`.specify/design/previews/*.handoff.json`,
`.specify/design/references.md`, `.specify/design/options.md`,
`.specify/design/design-system.json`, `.specify/design/review.md`, and stable design rules in
`.specify/memory/project-rules.md` when they truly become project defaults.

Create `.specify/design/design-brief.md` through
`specify-runtime artifact scaffold --kind design-brief --path .specify/design/design-brief.md`,
then refine only affected frontmatter fields and named sections through leased
`artifact patch` calls. The runtime expands the installed template; never read
and reproduce its stable boilerplate in memory. Infer repository evidence first, then ask one
high-impact design question at a time when the answer can change hierarchy,
density, component anatomy, motion, responsive/accessibility behavior,
reference fidelity, or approval scope. Do not ask for a production framework
merely to shape a framework-neutral preview. Confirm subject, audience, single
job, modules, locales, modes, platforms/viewports, comparison content,
component/state coverage, meaningful motion and `prefers-reduced-motion`, and
Must Preserve / May Adapt / Must Not boundaries. Record confirmed choices as
stable `DS-<KIND>-NNN` decisions with source, status, affected surfaces, and
verification; the brief is the decision ledger, not a chat transcript.

Read `{{specify-subcmd:specify-runtime design profiles}}` and select one or more
independent capability profiles: `web`, `mobile`, `desktop`, `cli`, `tui`, or
`content`. Hybrid products keep multiple profiles. If current repository
evidence proves `no-ui`, record `design_system_status: not-applicable` with that
evidence and exit without preview, approval, handoff, `ui-target`, or visual
comparison; never combine `no-ui` with a visual profile.

When creating a new direction or replacing a bootstrap seed, author
`.specify/design/previews/round-NN.manifest.json` from
`{{specify-subcmd:specify-runtime design preview-manifest --profiles <comma-separated-profile-ids> --out .specify/design/previews/round-NN.manifest.json}}`,
then render it with
`{{specify-subcmd:specify-runtime design preview --manifest .specify/design/previews/round-NN.manifest.json --out .specify/design/previews/round-NN.html}}`.
Do not hand-edit the generated HTML or globally replace direction IDs; the
renderer owns candidate metadata, the embedded manifest, URL targets, and
per-direction style scopes. Produce exactly three project-specific directions
in that one self-contained board. The deterministic profile model supplies
required capabilities, input modes, measurement units, specimen kinds, states,
and targets. All directions carry the same ordered `specimen_ids`, and every
acceptance row binds its profile's exact specimen set. Hold representative
content and coverage constant so direction differences are comparable. Use
modern native HTML/CSS—custom properties, cascade layers,
fluid scales, container queries, and progressive view transitions—with only
bounded inline review logic and no framework, CDN, remote runtime dependency,
network call, persistence, analytics, or business behavior.

Configure representative content for every specimen, boundaries, modes, every
decision-to-owner mapping, stable `DH-*` component/target/acceptance contracts,
structured comparison
tolerance, and the three directions in the compact manifest. The renderer produces the
matching candidate `spec-kit-design-preview-manifest-v1`; run
`{{specify-subcmd:specify-runtime design preview-lint .specify/design/previews/round-NN.html --level ready}}`,
and inspect direction switching, keyboard operation, responsive widths, state
coverage, motion, and reduced motion in a real browser. Present the exact round
path, direction IDs, and tradeoffs. Treat a requested hybrid as a new
inspectable composition in the next round. Iterate new numbered rounds until
the user approves; do not overwrite prior rounds or treat criticism as
approval. Freeze the approved round with
`{{specify-subcmd:specify-runtime design approve .specify/design/previews/round-NN.html --direction <direction-id> --format json}}`
and record
`approved_visual_ref: .specify/design/previews/round-NN.html#<direction-id>` in
the brief, review, and `DESIGN.md` `approval.visual_refs`, together with the
returned review round, preview/manifest/handoff SHA-256 values, approval and
selected-direction handoff sidecars, exact decision IDs, and exact handoff
contract IDs, capability profile IDs, and specimen IDs. Preserve the latter in
`DESIGN.md` `approval`, `capability_profiles`, and `specimens`. An edited
approved file or missing/stale sidecar is invalid.
Refinement that preserves an already approved direction needs no ceremonial
re-selection.

The visible handoff is part of what the user approves. Ready lint must reject
unknown/no-UI profiles, missing required capabilities/specimen kinds,
direction/specimen drift, or any required state, target, specimen, or `DS-*`
decision not covered by a `DH-*` visual acceptance row. `design approve`
projects the selected direction and complete capability model
into the immutable handoff; never manually rewrite that artifact or replace it
with a prose summary.

Create or revise root `DESIGN.md` only through `specify-runtime design export` from the approved round; use `assets/design-system.md` as the shape. Record only
decisions that constrain downstream UI work: principles, foundations, tokens,
component and interaction rules, responsive/accessibility behavior, reference
fidelity, and required visual evidence. Make exceptions explicit and
verifiable.

Set `design_system.status: approved`, record the selected direction and
product/repository source refs plus `approval.visual_refs`, review round,
preview/manifest/handoff SHA-256 values, immutable handoff ref, decision IDs,
and handoff contract IDs. Replace every asset
placeholder, run `{{specify-subcmd:specify-runtime design lint --level ready}}`, then export the
deterministic implementation contract with
`{{specify-subcmd:specify-runtime design export DESIGN.md --format json --out .specify/design/design-system.json}}`.
Do not hand off a structurally valid but generic or unapproved seed.

If `.specify/design/review.md` is absent, create its fixed shape with
`specify-runtime artifact scaffold --kind design-review --path .specify/design/review.md`;
otherwise query it through `artifact show`. Patch only its named sections with
the mode, inputs, approved direction, visual and handoff references, hashes,
decision and handoff contract IDs, covered platforms, risks, lint/export
results, and one recommended next workflow, using a fresh lease per section.
Never submit or reconstruct the whole review document. Ask the user to review the CLI-exported `DESIGN.md` before
recording the final design handoff; approval of an earlier
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
