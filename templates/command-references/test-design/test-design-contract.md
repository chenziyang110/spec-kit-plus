Trigger: when selecting a mode or artifact root, freezing scope, qualifying completeness, resolving test-material dispositions, validating, or handing off to Tasks.

Purpose: Preserve the planning-only Test Design lifecycle and its defensible completeness boundary outside the main-flow prompt.

Preserved Contract: One invocation selects `project-baseline`, `feature`, `incremental-update`, or `audit`; runtime-owned artifacts remain under `.specify/test-design/` or `<FEATURE_DIR>/test-design/`; every obligation, case, material, evidence item, exclusion, and gap stays traceable to the frozen source fingerprint.

The Leader freezes source refs, included and excluded paths, risk dimensions,
revision evidence, and the selected root before lane preparation. Feature mode
is optional after a completed Plan and before Tasks and must not mutate
`workflow.json`; project-baseline is standalone. Incremental update preserves
stable IDs only where current evidence still supports them. Audit never expands
or silently retargets the frozen source boundary.

Baseline and feature initialization are create-only. Incremental update and
audit are compare-and-swap transitions against an existing root: query status,
pass `--expected-revision`, preserve canonical IDs, and let the runtime reset
lane, validation, and handoff state. Audit rejects any frozen-boundary change.

The runtime owns `test-state.json`, `test-universe.json`, `test-catalog.json`,
`test-data-manifest.json`, `coverage-matrix.json`, `test-gaps.json`,
`lane-manifest.json`, accepted results, deterministic views, and
`handoff-to-tasks.json`, and mediates every mutation to those files. Workers
never write canonical artifacts, direct-write a runtime file, or perform a
whole-file merge. After inspecting and accepting bounded lane results, the
Leader selects the accepted truth. The Leader submits approved universe,
catalog, data, and coverage changes only through a fresh lease plus targeted
`artifact patch`, and submits approved gap rows only through runtime
`gap-reconcile`. `synthesize` validates the already-patched canonical bundle,
records its artifact digests, and advances runtime state; it does not
automatically materialize worker proposals. Only the runtime calculates claim
status and creates the Tasks handoff.

Every material has one disposition from `reuse`, `generate`, `search`,
`request`, `block`, or `defer`, with provenance, readiness, sensitivity,
licensing, reproducibility, sanitization, retention, cleanup, and applicable
case refs. Search uses primary or authoritative licensed sources. Production
customer data, secrets, credentials, and unlicensed material are forbidden.

Every `GAP-*` row has non-empty `affected_obligation_refs`; each reference must
point to a frozen `TO-*`, and every `TO-*` gap ref must point back to that row.
No exclusion, deferral, waiver, or blocking disposition may escape this
bidirectional accounting.

When the frozen scope is UI-bearing, consume the approved design and feature
UI contract as sources. Account for accessibility and structure, responsive
viewport/state behavior, motion and interaction, visual comparison or explicit
human review, and real-entrypoint runtime diagnostics. Preserve the required
`structure_snapshot`, `visual_capture`, and `runtime_diagnostics` evidence
classes; automated functional checks cannot replace visual acceptance.

The Leader binds accepted search output to the content-addressed evidence store
with `specify-runtime evidence register` for inline text/JSON and
`specify-runtime evidence import` for external or binary files. Missing external
feasibility, normative oracles, or disposable proof belongs to
`sp-deep-research`; resume Test Design from its evidence-backed Planning Handoff.
Verify that handoff, then have the Leader register or import the accepted object
under evidence scope `test-design`, preserving the Deep Research record and
Planning Handoff in provenance. Canonical Test Design rows cite the resulting
`test-design` record ref; they do not cite another scope directly.

The only completion states are `complete_against_frozen_scope`,
`qualified_with_declared_gaps`, `blocked`, and `stale`. The workflow must never
claim `absolutely_complete`. A feature handoff is pointer-only and preserves
test-case refs, test-data refs, gap and audit refs, and the frozen source
fingerprint for `sp-tasks`.
