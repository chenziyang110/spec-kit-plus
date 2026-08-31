Trigger: at every `$spx-design` entry or resume, before questions, route selection, or design-artifact mutation.

Purpose: classify natural-language design work behind one public skill while loading only the selected handler contract.

Preserved Contract: one public entrypoint routes create/refine/audit independently from reference synthesis, resumes active work first, and rejects domain-external work.

## Single Public Entry Point

Keep `$spx-design` as the single public entry point. Do not register or expose
`spx-design:create`, `spx-design:refine`, `spx-design:audit`, or equivalent
colon-namespaced skills. Persist the compact classification:

```text
task_type: create | refine | audit
input_strategy: context | synthesize
route_reason: <one evidence-based sentence>
```

Use `specify-runtime design change` for a new missing `UD-*` workspace or
`specify-runtime design iterate` for a successor of approved truth, then
use `specify-runtime artifact patch` to store the canonical route in
`.specify/design/changes/<UD-ID>/brief.md`. Treat
any selected-mode field exposed by
derived state only as a compatibility projection of `task_type`; use the same
owner CLI to repeat the route in review when it explains closeout.

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

## Resume Before Reclassification

Query `.specify/design/index.json` and the matching change brief/contract first
through targeted `specify-runtime artifact show` calls only when they exist or
registered metadata identifies them. Missing registration is legitimate
discovery absence; do not blindly artifact-show a missing index.
Never use an unregistered root design document as workflow input. Resume before reclassification when
the same objective is nonterminal, using the brief's task type and input
strategy plus the derived state's current stage. Approval, feedback, and
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
