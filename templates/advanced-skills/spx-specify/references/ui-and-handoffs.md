# UI intake

Read this for any substantive user-visible UI change, not only when a screenshot
was supplied. Confirmed discussion state is governed by
`discussion-handoff.md`.

Create `ui-brief.md` from `assets/ui-brief.md`. In `spec-contract.json`, set
`design_contract.ui_applicable: true`, `ui_work_type`,
`surface_type`, `platforms`, `ui_brief_ref`, and the
matching `design_system_status`; also carry the brief and original source paths
in the relevant design/fidelity refs. Record:

- subject, audience, single job, visual/content/interaction theses, signature,
  and the approved visual ref;
- when supplied by design, the exact immutable project-level
  `round-NN.html#direction-id`, approval sidecar, preview/manifest SHA-256
  values, applicable `DS-*` decisions, motion tokens, and reduced-motion
  equivalent;
- real entry points, surface/platform classification, experience intent, and
  information hierarchy;
- approved `DESIGN.md` rules, tokens/components, and any explicit extension;
- layout, hierarchy, interaction, responsive, accessibility, and required state
  constraints; must-preserve, may-adapt, and must-not decisions;
- a viewport/state acceptance matrix and later visual evidence.
- real content and image plans; per-reference use intent; and required
  `structure_snapshot`, `visual_capture`, `runtime_diagnostics`, and
  `visual_comparison_or_human_review` evidence.

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
When a feature target materially reduces ambiguity, scaffold it with
`{{specify-subcmd:design ui-target --out <FEATURE_DIR>/ui-target.html}}`, configure its
embedded manifest and candidate status, and require
`{{specify-subcmd:design ui-target-lint <FEATURE_DIR>/ui-target.html --level ready}}`.
