# UI intake

Read this for any substantive user-visible UI change, not only when a screenshot
was supplied. Confirmed discussion state is governed by
`discussion-handoff.md`.

Create `ui-brief.md` through `specify-runtime artifact scaffold --kind ui-brief --path <feature-dir>/ui-brief.md`, then fill only its semantic sections through leased `artifact patch` calls; use `assets/ui-brief.md` only as compact field guidance, never as a block to reproduce. When original references exist, create `ui-reference-notes.md` through `artifact scaffold --kind ui-reference-notes` and patch its observed facts. Patch the related `spec-contract.json` fields through leased JSON-pointer `artifact patch`. Set
`design_contract.ui_applicable: true`, `ui_work_type`,
`surface_type`, `platforms`, `ui_brief_ref`, and the
matching `design_system_status`; also carry the brief and original source paths
in the relevant design/fidelity refs. Record:

- subject, audience, single job, visual/content/interaction theses, signature,
  and the approved visual ref;
- when supplied by design, the exact immutable project-level
  `round-NN.html#direction-id`, approval sidecar, preview/manifest/handoff
  SHA-256 values, immutable handoff ref, applicable `DS-*` decisions and
  `DH-*` handoff contracts, motion tokens, and reduced-motion equivalent;
- real entry points, surface/platform classification, experience intent, and
  information hierarchy;
- approved `DESIGN.md` rules, tokens/components, and any explicit extension;
- layout, hierarchy, interaction, responsive, accessibility, and required state
  constraints; must-preserve, may-adapt, and must-not decisions;
- a viewport/state acceptance matrix and later visual evidence.
- real content and image plans; per-reference use intent; and required
  `structure_snapshot`, `visual_capture`, `runtime_diagnostics`, and
  `visual_comparison_or_human_review` evidence.
- **UI Requirements** and **UI Acceptance Criteria** plus Design Intelligence
  fields: design DNA / personality, dials (`variance` / `motion` / `density`)
  when known, surface type, anti-slop locks subordinate to approved `DESIGN.md`,
  UI System Model refs (tokens/components/states/responsive), required state
  matrix, and quality rules that forbid generic dashboard/template patterns.
  Inherit discussion `design_context` when the handoff carries it.

When original UI references exist, preserve inspectable source paths or URLs and
record fidelity as `approximate` by default, `high`, or `inspiration`.
`approximate` and `high` activate Reference-Implementation evidence: reference
source evidence, fidelity criteria, verification entry points, difference
inventory, and accepted deviations. `high` requires explicit visual comparison
and deviation recording.

Do not infer hidden behavior from a screenshot. Do not reduce original visual
inputs to prose when downstream implementation needs to inspect them. If
`DESIGN.md` is bootstrap/unapproved and the feature needs a new direction, stop
and route to `$spx-design` instead of inheriting starter aesthetics.
Do not substitute feature-level `ui-target.html` for an approved project-level
design preview; preserve both references when both apply.
Do not restate the approved handoff from memory. Select task-relevant `DH-*`
IDs from the immutable handoff, copy their structured rows unchanged, and mark
feature-only extensions with their own source instead of altering an approved
row.
When a feature target materially reduces ambiguity, scaffold it with
`{{specify-subcmd:specify-runtime design ui-target --out <FEATURE_DIR>/ui-target.html}}`, configure its
embedded manifest and candidate status, and require
`{{specify-subcmd:specify-runtime design ui-target-lint <FEATURE_DIR>/ui-target.html --level ready}}`.
