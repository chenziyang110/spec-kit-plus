Trigger: at every `$spx-design` entry or resume, before questions, route selection, or design-artifact mutation.

Purpose: classify natural-language design work behind one public skill while loading only the selected handler contract.

Preserved Contract: one public entrypoint routes create/refine/audit independently from reference synthesis, resumes active work first, and rejects domain-external work.

## Single Public Entry Point

Keep `$spx-design` as the single public entry point. Do not register or expose
`spx-design:create`, `spx-design:refine`, `spx-design:audit`, or equivalent
colon-namespaced skills. Persist the compact classification:

```text
contract_action: create | refine | audit
surface_posture: greenfield | inherit-existing | page-overhaul-authorized
input_strategy: context | synthesize
route_reason: <one evidence-based sentence>
```

Use `specify-runtime design change` for a new missing `UD-*` workspace or
`specify-runtime design iterate` for a successor of approved truth, then
use `specify-runtime artifact patch` to store the canonical route in
`.specify/design/changes/<UD-ID>/brief.md`. Treat
any selected-mode field exposed by
derived state only as a compatibility projection of `contract_action`; use the same
owner CLI to repeat the route in review when it explains closeout.

`contract_action` describes the `UD-*` artifact lifecycle, not permission to
redraw a product. `surface_posture` describes visual authority and must exactly
match `style_authority.mode`. Creating a missing design contract for a live
product is `contract_action: create` plus `surface_posture: inherit-existing`,
never a greenfield page.

## Classification

- `create`: allocate a bounded greenfield or extension change when no matching
  nonterminal workspace exists.
- `refine`: continue an unapproved change or allocate a digest-pinned successor
  with `specify-runtime design iterate`; never mutate approved truth or
  hand-author `iteration_of` / `basis_sha256` lineage.
- `audit`: inspect a declared scope, provenance, adoption, or drift without
  mutating approved truth.
- `context`: use confirmed product context and verified live evidence.
- `synthesize`: use references with explicit intents
  (`mood` | `layout` | `type` | `color-only` on reference boards). Synthesize is
  an input strategy, not a terminal task type; attach it to create or refine.
  References are evidence, not a license to copy protected brand or artwork.
- Taste intake is required for visual create and substantive refine before
  single-concept preview work: `design_read`, dials with inference reason,
  `aesthetic_family`, `foundation_strategy`, `redesign_mode` when live UI
  exists, and surface-aware `anti_slop_locks`. Do not expose colon-namespaced
  design skills (including taste variants).

## Direction checkpoints

Use the same platform-neutral flow for every substantive route:
`intake -> concept-calibration -> direction-confirmed -> contract-completion ->
formal-approval -> register`. Stage 1 keeps one current concept and a stage 1
minimum viable contract: exact scope, selected profiles, subject, audience,
single job, taste, primary layout/signature, layout-changing critical state,
accessibility contrast/focus feasibility, reduced-motion feasibility, and one
stress target. Use 2-3 textual choices only to answer one material ambiguity;
do not generate three full boards and do not auto-add an unselected profile.
Run `preview-lint concept` first and require its current byte-bound concept
receipt; when inspection is available, pass the protected-surface review
through `--inspection-json`. Only after that receipt exists may the workflow
ask for explicit direction confirmation, and only after the user confirms may
it call `direction-confirm`. A lint pass alone must not create the direction sidecar. The
direction-confirmed sidecar is non-consumable, not approval, not register, and
not a downstream binding. Full source continuity denominator, mature adoption,
complete matrices, and `DH-*` handoff rows wait for contract-completion.
Contract-completion starts from the next numbered round because a
`.direction.json` round must never be formal approved; inherit the confirmed
visual direction by default, and revise that new round only if matrix work
exposes a necessary visual change.

## Resume Before Reclassification

Query `.specify/design/index.json` and the matching change brief/contract first
through targeted `specify-runtime artifact show` calls only when they exist or
registered metadata identifies them. Missing registration is legitimate
discovery absence; do not blindly artifact-show a missing index.
Never use an unregistered root design document as workflow input. Resume before reclassification when
the same objective is nonterminal, using the brief's contract action, surface
posture, and input strategy plus the derived state's current stage. Approval, feedback, and
continuation are lifecycle events for the active task. Reclassify only for an
explicit objective change or evidence that the stored route cannot safely
finish, and record that delta.

Derive each stable path-like surface ID from confirmed source or registered
metadata; split surfaces and never pass the whole brief or prose as `--scope`.
Run `specify-runtime design resolve --scope <exact-surface> --format json` for
registered coverage. It is discovery only, never adoption. Split a composite
result into independently bound consumer units. Current binding artifacts are
singular, so each unit owns one exact scope and one binding artifact; do not
invent one merged or “latest” contract.

## Route Matrix

| Truth and intent | Route |
| --- | --- |
| No matching draft; establish a bounded design | `create/context` |
| No matching draft plus shaping references | `create/synthesize` |
| Approved scoped truth must intentionally change | new `refine/context` successor via `design iterate` |
| References shape an intentional replacement | new `refine/synthesize` successor via `design iterate` |
| Readiness, consistency, provenance, or drift check only | `audit/context` |

Use approval status to break create/refine ambiguity. Start audit/mutation
ambiguity as audit and promote only after evidence proves truth must change.
Treat proven `no-ui` as a terminal applicability result, never a visual mode.

Resolve `style_authority` before the professional skill route. Existing-product
feature, component, or partial functional-page work is `inherit-existing`: cite
live sources, protect `global-shell` and `shared-components`, allow no style
delta, and select no style skill. Use `page-overhaul-authorized` only for an
explicitly approved exact complete-page visual overhaul; sibling pages, shared
components, and shell stay protected. A local feature or function-page refactor
does not authorize a new style. `greenfield` requires evidence that no live UI
language applies.

Route feature behavior and acceptance to `$spx-specify` or user-selected
`$spx-quick`, implementation architecture to `$spx-plan`, durable engineering
principles to `$spx-constitution`, and code drift against correct design to
`$spx-review` or the active implementation workflow. If a planning-ready source
spec already owns unchanged requirements, persist `post-specify` and return to
Plan through `formal-post-specify`; do not run a second Specify. Only a real
requirements, scope, or acceptance change reopens Specify.
