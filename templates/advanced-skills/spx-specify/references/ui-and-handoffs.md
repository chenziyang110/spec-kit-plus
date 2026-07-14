# UI intake

Read this for any substantive user-visible UI change, not only when a screenshot
was supplied. Confirmed discussion state is governed by
`discussion-handoff.md`.

Create `ui-brief.md` from `assets/ui-brief.md`. In `spec-contract.json`, set
`design_contract.ui_applicable: true`, `ui_work_type`, `ui_brief_ref`, and the
matching `design_system_status`; also carry the brief and original source paths
in the relevant design/fidelity refs. Record:

- real entry points, user job, experience intent, information hierarchy, and a
  recognizable visual/interaction signature;
- approved `DESIGN.md` rules, tokens/components, and any explicit extension;
- layout, hierarchy, interaction, responsive, accessibility, and required state
  constraints; must-preserve, may-adapt, and must-not decisions;
- a viewport/state acceptance matrix and later visual evidence.

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
