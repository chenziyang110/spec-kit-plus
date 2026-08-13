# UI intake

Read this for any substantive user-visible UI change, not only when a screenshot
was supplied. Confirmed discussion state is governed by
`discussion-handoff.md`.

Run `specify-runtime design resolve --scope <exact-surface> --format json`, then
query `.specify/design/index.json` and the exact change-local `DESIGN.md` /
`design-contract.json` for every returned registered candidate. Resolve is
discovery only and never selects “latest” or adopts. The current formal binding
is singular, so split `composite: true` coverage into independently bound
feature units, each with one exact scope, `spec-contract.json`, and
`ui-brief.md`. Create `ui-brief.md` through
`specify-runtime artifact scaffold --kind ui-brief --path <feature-dir>/ui-brief.md`, then fill only its adoption and feature-delta sections through leased `artifact patch` calls; use `assets/ui-brief.md` only as compact field guidance, never as a block to reproduce. When original references exist, create `ui-reference-notes.md` through `artifact scaffold --kind ui-reference-notes` and patch its observed facts. Patch the related `spec-contract.json` fields through leased JSON-pointer `artifact patch`. Set
`design_contract.ui_applicable: true`, `ui_work_type`,
`surface_type`, `platforms`, `ui_brief_ref`, and the
matching `design_system_status`; also carry the `UD-*` ID, exact design/change
contract refs, registered contract SHA-256, brief, and original source paths in
the relevant design/fidelity refs. Record:

- subject, audience, single job, visual/content/interaction theses, signature,
  and the approved visual ref;
- when supplied by design, the exact immutable change-level
  `round-NN.html#direction-id`, approval sidecar, preview/manifest/handoff
  SHA-256 values, immutable handoff ref, applicable `DS-*` decisions and
  `DH-*` handoff contracts, motion tokens, and reduced-motion equivalent;
- real entry points, surface/platform classification, experience intent, and
  information hierarchy;
- approved change-local `DESIGN.md` rows, tokens/components, and any explicit
  feature-only delta;
- layout, hierarchy, interaction, responsive, accessibility, and required state
  constraints; must-preserve, may-adapt, and must-not decisions;
- a viewport/state acceptance matrix and later visual evidence.
- real content and image plans; per-reference use intent; and required
  `structure_snapshot`, `visual_capture`, `runtime_diagnostics`, and
  `visual_comparison_or_human_review` evidence.
- **UI Requirements** and **UI Acceptance Criteria** plus Design Intelligence
  fields: design DNA / personality, dials (`variance` / `motion` / `density`)
  when known, surface type, anti-slop locks subordinate to the selected change,
  UI System Model refs (tokens/components/states/responsive), required state
  matrix, and quality rules that forbid generic dashboard/template patterns.
  Inherit discussion `design_context` when the handoff carries it.

Before replacing a formal feature binding, run
`specify-runtime design diff <CURRENT-UD-ID> <CANDIDATE-UD-ID> --format json`
and retain its scope, `DS-*`, `DH-*`, and changed-section delta. Then run
`specify-runtime design impact feature:<feature-id> --change <CANDIDATE-UD-ID> --scope <exact-surface> --mode formal --expected-change <CURRENT-UD-ID|none> --format json`
before patching. Present `preserved_bindings`, `invalidated_bindings`, and
`reconcile_from`. Use fresh
leased `specify-runtime artifact patch` calls to set the full four-field
replacement in `spec-contract.json` and `ui-brief.md` first; hash the exact
spec-contract bytes, then run
`specify-runtime design adopt feature:<feature-id> --change <UD-ID> --scope <exact-surface> --mode formal --binding-ref <feature-dir>/spec-contract.json --binding-sha256 <sha256> --expected-change <CURRENT-UD-ID|none> --format json`.
Only a successful compare-and-swap receipt authorizes downstream invalidation
and regeneration; failure leaves the earlier binding authoritative. On
success, reconcile from the receipt's named stage, mark only listed downstream
bindings and affected Review evidence pending, preserve completed implementation
and unaffected evidence, and never directly rewrite another stage's artifact.

When original UI references exist, preserve inspectable source paths or URLs and
record fidelity as `approximate` by default, `high`, or `inspiration`.
`approximate` and `high` activate Reference-Implementation evidence: reference
source evidence, fidelity criteria, verification entry points, difference
inventory, and accepted deviations. `high` requires explicit visual comparison
and deviation recording.

Do not infer hidden behavior from a screenshot. Do not reduce original visual
inputs to prose when downstream implementation needs to inspect them. If
no applicable registered change exists and the feature needs a new direction,
stop and route to `$spx-design` instead of improvising or mutating legacy truth.
Do not substitute feature-level `ui-target.html` for an approved change-level
design preview; preserve both references when both apply.
Do not restate the approved handoff from memory. Select task-relevant `DH-*`
IDs from the immutable handoff, copy their structured rows unchanged, and mark
feature-only extensions with their own source instead of altering an approved
row.
When a feature target materially reduces ambiguity, scaffold it with
`{{specify-subcmd:specify-runtime design ui-target --out <FEATURE_DIR>/ui-target.html}}`, configure its
embedded manifest and candidate status, and require
`{{specify-subcmd:specify-runtime design ui-target-lint <FEATURE_DIR>/ui-target.html --level ready}}`.
