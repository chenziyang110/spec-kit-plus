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

Use `specify-runtime artifact patch` to store the canonical route in
`.specify/design/design-brief.md`. Treat any selected-mode field exposed by
derived state only as a compatibility projection of `task_type`; use the same
owner CLI to repeat the route in review when it explains closeout.

## Classification

- `create`: replace missing/bootstrap truth with the first approved baseline.
- `refine`: create a new immutable approval for project-wide changes to an
  approved system.
- `audit`: inspect readiness, provenance, adoption, or drift without mutating
  approved truth.
- `context`: use confirmed product context and verified live evidence.
- `synthesize`: use references with explicit intents
  (`mood` | `layout` | `type` | `color-only` on reference boards). Synthesize is
  an input strategy, not a terminal task type; attach it to create or refine.
  References are evidence, not a license to copy protected brand or artwork.
- Taste intake is required for visual create and project-wide refine before
  three-direction preview work: `design_read`, dials with inference reason,
  `aesthetic_family`, `foundation_strategy`, `redesign_mode` when live UI
  exists, and surface-aware `anti_slop_locks`. Do not expose colon-namespaced
  design skills (including taste variants).

## Resume Before Reclassification

Query design state and design brief first. Resume before reclassification when
the same objective is nonterminal, using the brief's task type and input
strategy plus the derived state's current stage. Approval, feedback, and
continuation are lifecycle events for the active task. Reclassify only for an
explicit objective change or evidence that the stored route cannot safely
finish, and record that delta.

## Route Matrix

| Truth and intent | Route |
| --- | --- |
| Missing/bootstrap design; establish baseline | `create/context` |
| Missing/bootstrap design plus shaping references | `create/synthesize` |
| Approved design; change project-wide truth | `refine/context` |
| Approved design; references shape that change | `refine/synthesize` |
| Readiness, consistency, provenance, or drift check only | `audit/context` |

Use approval status to break create/refine ambiguity. Start audit/mutation
ambiguity as audit and promote only after evidence proves truth must change.
Treat proven `no-ui` as a terminal applicability result, never a visual mode.

Route feature behavior and acceptance to `$spx-specify` or user-selected
`$spx-quick`, implementation architecture to `$spx-plan`, durable engineering
principles to `$spx-constitution`, and code drift against correct design to
`$spx-review` or the active implementation workflow.
