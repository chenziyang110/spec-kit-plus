# Discussion handoff

Use this only when requirements span turns or an existing confirmed discussion
must feed the specification. Prefer the installed deterministic discussion
commands for resolve, init, resume, handoff validation, ready, and consumed
state.

First run `{{specify-subcmd:specify-runtime discussion resolve --intent sp-specify --json}}`,
appending `--slug <slug>` when an exact slug was supplied.
If multiple candidates are returned, ask for the exact slug; never guess, never
select latest, and never infer an unstated slug from a name, title, topic, or
keyword similarity. Carry the resolver's `review_digest`, `state_sha256`, selected slug,
and `recommended_consumer` through consumption.

Respect topic ownership: only `continue_current` material belongs to the
resolved handoff. `branch_new`, `link_existing`, and `defer` routed topics are
reference-only and must not be silently compiled into this spec.

Before consuming, run
`{{specify-subcmd:specify-runtime discussion validate-handoff <slug> --mode ready --json}}`. Require `status:
handoff-ready`, `version: 5`, a current `discussion_snapshot_digest`, `recommended_consumer: sp-specify`,
`consumer_eligibility.sp-specify.status: ready`,
`planning_gate_status: ready`, `quality_gate.status: user_confirmed`,
matching `quality_gate.confirmed_digest` and `review_digest`, zero hard
unknowns, zero open conflicts, complete protected obligations, non-empty actors,
scenarios, scope, success criteria, and optimal solution approach, and a target
project root matching the active project. Require every `source_materials` entry
to be inspected, gap-free, and linked through `source_evidence.material_id`.
Require `topic_ownership.owner_slug`
to match the resolved slug; routed topics are cross-discussion pointers, not
specification input. Fail closed to `$spx-discussion` with field errors and a
safe retry; do not reconstruct or patch upstream truth.

After feature creation resolves `FEATURE_DIR`, before compiling the Spec body
or source-to-acceptance mappings, declare its source intent through:

`{{specify-subcmd:specify-runtime discussion bind-consumer <slug> --feature-dir <feature-dir> --review-digest <review_digest> --intake --input-json '<transition-json>' --format json}}`

Use the current resolver digest and existing input shape `semantic_delta: []`,
`required_refs: []`, `blockers: []`, `recovery: null`. The source must already
be complete, user-confirmed, currently ready, and selected for `sp-specify`.
Intake writes `brainstorming/handoff-to-specify.json` at `status: pending` with
all five lineage fields: `discussion_slug`, `source_contract`, `review_digest`,
`state_sha256`, `recommended_consumer`. Pending intent cannot be consumed; it
does not claim compiled Spec readiness. No additional human approval is needed.
Matching pending intake is idempotent. Reuse a matching ready binding without
running intake again; never downgrade it. Different source/digest bindings
block. The Agent must not delete the pointer, clear its lineage, or detach Spec
`source_contract` / `source_revision`. A failed intake blocks compilation;
do not continue as an unbound direct request.

Keep one compact decision digest containing confirmed scope, rejected options,
assumptions, unresolved user-owned decisions, source-material/evidence links,
UI/reference inputs, and the current semantic delta. Confirm the digest before
treating it as authoritative.

A handoff is usable only when its referenced evidence exists, blocking
questions are resolved or explicitly retained, and the specification can trace
every material confirmed decision. If live repository evidence contradicts the
handoff, surface the conflict; do not silently favor either source.

After complete compilation and normal self-review, upgrade the existing
pending source intent with the default command without --intake:
`specify-runtime discussion bind-consumer <slug> --feature-dir <feature-dir> --review-digest <review_digest> --input-json '<transition-json>'`.
Always use the resolver-returned `review_digest`; never infer, omit, or
reconstruct it from the handoff bytes. Default binding retains the strict
compiled-Spec/source-coverage validation before making its pointer ready; it
is not the first source-intent bind.
Mark the handoff consumed only after validation and successful compilation into
the spec contract. `$spx-discussion` owns the producer lifecycle; this reference
only governs safe consumption, and discussion is never mandatory for a clear
request.
## Source requirement coverage

For material-backed intake, validate the ready Discussion source before
compilation. Require complete runtime-owned `reading`, full unit delivery,
`unit_dispositions`, and `agent_requirement_contract.source_requirements`.
Old material records without reading receipts must return to Discussion for
import and rereading; never infer full consumption from `inspected`, empty
gaps, a summary, or an old ready flag. Pure conversation with no materials
retains its existing path. This check adds no duplicate human confirmation.

Set `spec-contract.json.source_contract` to the canonical discussion handoff
path and `source_revision` to its exact `review_digest`. Populate
`source_requirement_coverage` with exactly one row per upstream REQ, preserving
`requirement_id` and `disposition`. Every `in_scope` row has non-empty
`requirement_refs` to real values such as
`spec-contract.json#/scope/in/0` or
`spec-contract.json#/capability_operations/0`, and `acceptance_refs` to real
`spec-contract.json#/acceptance_criteria/N` values. Inspect those referenced
values and preserve the source rule's conditions, negations, permissions,
exceptions, and observable acceptance; pointing at generic scope prose is not
semantic coverage. Keep each mapping consistent with `acceptance_coverage`.

For `context`, `deferred`, `out_of_scope`, and `duplicate`, retain the source
ID/disposition with empty `requirement_refs` and `acceptance_refs`; a duplicate
also preserves exact `duplicate_of`, resolving to an existing retained REQ
without cycles. Decision sources, reasons, and reopen conditions remain bound
in the upstream source ledger. An unresolved source rule blocks readiness.
Never remove an upstream REQ to make the coverage count agree. Do not retell or
reextract unchanged original sources: verify complete mappings by stable refs
and return true omissions or interpretation conflicts to their owning phase.
