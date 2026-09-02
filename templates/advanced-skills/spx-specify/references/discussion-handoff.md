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
handoff-ready`, `recommended_consumer: sp-specify`,
`consumer_eligibility.sp-specify.status: ready`,
`planning_gate_status: ready`, `quality_gate.status: user_confirmed`,
matching `quality_gate.confirmed_digest` and `review_digest`, zero hard
unknowns, zero open conflicts, complete protected obligations, and a target
project root matching the active project. Require `topic_ownership.owner_slug`
to match the resolved slug; routed topics are cross-discussion pointers, not
specification input. Fail closed to `$spx-discussion` with field errors and a
safe retry; do not reconstruct or patch upstream truth.

Keep one compact decision digest containing confirmed scope, rejected options,
assumptions, unresolved user-owned decisions, UI/reference inputs, and the
current semantic delta. Confirm the digest before treating it as authoritative.

A handoff is usable only when its referenced evidence exists, blocking
questions are resolved or explicitly retained, and the specification can trace
every material confirmed decision. If live repository evidence contradicts the
handoff, surface the conflict; do not silently favor either source.

Bind the feature compatibility pointer with
`specify-runtime discussion bind-consumer <slug> --feature-dir <feature-dir> --review-digest <review_digest> --input-json '<transition-json>'`.
Always use the resolver-returned `review_digest`; never infer, omit, or
reconstruct it from the handoff bytes.
Mark the handoff consumed only after validation and successful compilation into
the spec contract. `$spx-discussion` owns the producer lifecycle; this reference
only governs safe consumption, and discussion is never mandatory for a clear
request.
