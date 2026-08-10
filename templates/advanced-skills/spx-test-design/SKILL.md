---
name: spx-test-design
description: Independent planning-only test intelligence producer for advanced coding models. Use when a project or feature needs a frozen test universe, traceable professional test cases, explicit test-data decisions, an independent coverage audit, a published package, or typed consumer projections.
---

# SPX Test Design

Read `references/project-learning.md` and apply its consume-capture policy.
Read `references/project-cognition.md`, using cognition intent `test_design`.
Always read `references/test-design-contract.md`. Read
`references/native-subagents.md` and `references/worker-contract.md` when lanes
are delegated. Read `references/consequence-gate.md` when its triggers apply and
`references/ui-quality-gate.md` when the frozen scope is UI-bearing. Read
`references/blocker-resolution.md` before a blocked exit.

This is a planning-only workflow. Source, tests, repository fixtures,
migrations, production configuration, and build tooling are read-only. Design
tests and their material package; do not implement, execute, or repair tests.
The Leader owns scope, canonical artifacts, lane acceptance, synthesis,
independent audit, validation, publication, projections, and the compatibility
Tasks handoff.

## Select and freeze the run

Select exactly one mode:

- `project-baseline`: scan a declared project boundary and use
  `.specify/test-design/`.
- `feature`: design from an explicitly selected feature boundary and use
  `<FEATURE_DIR>/test-design/`.
- `incremental-update`: CAS-reenter an existing root against an explicit source
  delta while preserving semantically unchanged stable IDs.
- `audit`: CAS-reenter an existing package for assessment without expanding its
  frozen boundary.

`$spx-test-design` is an **independent producer** and does not require Plan
completion or a completed Plan. For feature-scoped work, resolve the feature
explicitly. If a feature workflow exists, query
`{{specify-subcmd:specify-runtime workflow show --feature-dir <feature-dir> --format json}}`
only to bind current sources and consumer context; never edit
`FEATURE_DIR/workflow.json` or transition its required stage. The default formal
path may still select Test Design between `$spx-plan` and `$spx-tasks`, but a
project or feature run may begin independently from current evidence.

Before discovery, freeze the query, source refs, included and excluded paths,
risk dimensions, and runtime-computed fingerprint. Include the applicable
capabilities, requirements, entrypoints, environments, operational risks, and
UI surfaces. Current code is final authority for implemented behavior; tests,
configuration, official contracts, and live runtime evidence corroborate it.
Project Cognition is navigation only and no cognition claim may replace code
verification. A specification or Plan may supply an
intended-behavior basis but is not an entry prerequisite. Do not claim coverage
outside the frozen denominator. Initialize through
one of these runtime-owned forms, passing the frozen input as JSON:

```text
{{specify-subcmd:specify-runtime test-design init --scope project --mode project-baseline --leader-id <leader-id> --input-json <json> --format json}}
{{specify-subcmd:specify-runtime test-design init --scope feature --mode feature --feature-dir <feature-dir> --leader-id <leader-id> --input-json <json> --format json}}
```

On resume, run
`{{specify-subcmd:specify-runtime test-design status --feature-dir <feature-dir> --format json}}`
(omit `--feature-dir` for project scope) and continue from its phase, revision,
accepted results, blockers, and source fingerprint; never reconstruct state
from chat or overwrite runtime-owned state files. `next_action` expresses the
default formal Tasks route; for an explicitly selected Plan or Quick consumer
at validated feature state, use the permitted direct `publish` branch below
instead of `handoff`. Reenter an existing root only
through one of these compare-and-swap forms using the revision returned by
`status`:

```text
{{specify-subcmd:specify-runtime test-design init --scope project --mode incremental-update --leader-id <leader-id> --expected-revision <revision> --input-json <json> --format json}}
{{specify-subcmd:specify-runtime test-design init --scope feature --mode audit --feature-dir <feature-dir> --leader-id <leader-id> --expected-revision <revision> --input-json <json> --format json}}
```

Both reentry modes support project and feature roots; choose the original
`--scope` and include `--feature-dir` only for the original feature root.
`incremental-update` may change the explicitly frozen source set and must retain
unchanged canonical IDs. `audit` must keep the existing source refs, included
and excluded paths, and risk dimensions unchanged; the runtime refreshes the
content fingerprint from those same sources. Both reentry modes let the runtime
invalidate the prior lane, validation, audit, and handoff state; never imitate
that reset with direct file edits. Stop on a revision mismatch and rerun
`status` before deciding whether to retry.

For every later mutation, treat the envelope's `next_argv` or
`checkpoint_argv_prefix` as authoritative and retain its current
`--expected-revision`. The examples below show the command shape; never retype
an argv from an older revision. `lane-yield` is the exception and is bound by
the active lane and attempt IDs plus a non-empty auditable reason.

## Build the universe and discovery lanes

Inspect initialized artifacts with `specify-runtime artifact show`. Populate
the canonical universe, catalog, data manifest, and coverage matrix only with
fresh leased JSON-pointer `artifact patch` operations; never submit or rewrite
them whole. Preserve stable `CAP-*`, `SCN-*`, `TC-*`, `TD-*`, `COV-*`, and
`GAP-*` IDs. Then run:

```text
{{specify-subcmd:specify-runtime test-design universe-build --feature-dir <feature-dir> --expected-revision <revision> --format json}}
{{specify-subcmd:specify-runtime test-design lane-prepare --feature-dir <feature-dir> --expected-revision <revision> --input-json <lane-json> --format json}}
```

Omit `--feature-dir` for a project root. Create bounded, non-overlapping lanes
from uncovered obligations and risks. A packet must declare its obligation IDs,
read paths, questions, frozen fingerprint, evidence expectations, and result
shape. Every substantive discovery lane must be leased to and executed by a
non-Leader worker; the Leader plans packets, reviews candidates, accepts lanes,
and synthesizes, but never substitutes for discovery. If no subagent is
available, leave the lane pending or yield the active attempt with a non-empty
reason, then stop blocked at that lane and resume there when a worker is
available.

For each packet, the Leader or worker follows the lease lifecycle:

```text
{{specify-subcmd:specify-runtime test-design lane-lease --feature-dir <feature-dir> --expected-revision <revision> --worker-id <worker-id> --format json}}
{{specify-subcmd:specify-runtime test-design lane-checkpoint --feature-dir <feature-dir> --expected-revision <revision> --lane-id <lane-id> --attempt-id <attempt-id> --result-json <json> --format json}}
<execute the lease response's yield_argv_prefix with --reason <reason>>
{{specify-subcmd:specify-runtime test-design lane-accept --feature-dir <feature-dir> --expected-revision <revision> --lane-id <lane-id> --attempt-id <attempt-id> --format json}}
```

Use the returned `yield_argv_prefix` (owned verb `specify-runtime test-design lane-yield`) with the exact non-empty interruption or blocker reason for a
blocked, interrupted, or no-longer-safe attempt. A worker's successful
checkpoint is still only a candidate. The Leader checks
packet-bounded reads, evidence, contradictions, unknowns, gaps, case quality,
and data hygiene before `lane-accept`; a worker must never accept its own result.

## Synthesize test cases and the materials package

Only after every required discovery lane is accepted or has an explicit gap
disposition, review the accepted proposals, register accepted evidence,
reconcile duplicates and contradictions, patch approved case/data/coverage
changes through fresh leased JSON-pointer artifact operations, and submit approved
gap rows through
`{{specify-subcmd:specify-runtime test-design gap-reconcile --feature-dir <feature-dir> --expected-revision <revision> --leader-id <leader-id> --input-json <gap-json> --format json}}`.
The runtime atomically maintains `GAP-*` plus reverse `TO-*` / `COV-*` refs. Then run
`{{specify-subcmd:specify-runtime test-design synthesize --feature-dir <feature-dir> --expected-revision <revision> --leader-id <leader-id> --format json}}`.
Synthesize validates the merged canonical truth; it does not silently materialize
worker proposals. Each case must have traceable requirements,
capabilities, scenarios, priority, stage, preconditions, procedure when
applicable, a deterministic oracle or pass criteria, verification method,
evidence requirements, and `TD-*` references.

Resolve every material requirement with exactly one disposition: `reuse`,
`generate`, `search`, `request`, `block`, or `defer`. Record readiness,
provenance, sensitivity, PII status, sanitization, retention, and the required
recipe, request instructions, or unblock criteria. Prefer synthetic or curated
fixtures. Never copy production customer data or expose secrets merely to make
a dataset ready.

Workers may propose search evidence, but only the Leader may validate its
authority, licensing, reproducibility, source, and provenance and accept it into
the content-addressed evidence store. Register accepted inline text or JSON with
`{{specify-subcmd:specify-runtime evidence register --content '<payload>' --scope test-design --source <source> --provenance <provenance>}}`
and import accepted external or binary material with
`{{specify-subcmd:specify-runtime evidence import --file <path> --scope test-design --source <source> --provenance <provenance>}}`.
Verify the returned record and cite its `evidence_id` or `record_ref` from the
material and coverage rows; a URL or worker summary alone is not accepted
evidence.

When the missing truth is external feasibility, a normative oracle, a
disposable proof, or evidence that bounded read-only search cannot establish,
stop with the affected coverage and gap refs and route to
`$spx-deep-research`. Do not invoke it in this run. Resume Test Design only from
its primary-source findings, evidence records, and `Planning Handoff`; then CAS
reenter the test-design root when those findings change the frozen inputs.

## Audit, validate, publish, and project

After synthesis, run
`{{specify-subcmd:specify-runtime test-design audit-prepare --feature-dir <feature-dir> --expected-revision <revision> --format json}}`.
Lease the resulting `AUDIT-*` lane to a worker identity that is neither the
Leader nor any accepted discovery worker. If no independent worker is
available, leave the lane pending or yielded and block validation and handoff. The auditor
challenges omitted requirements and risk dimensions, weak oracles, unsupported
evidence, missing states and boundaries, infeasible harness assumptions, unsafe
data, duplicate cases, and broken reverse traceability. Checkpoint and accept
the audit through the same lane commands; the synthesizer must not self-certify
completeness.

Run
`{{specify-subcmd:specify-runtime test-design validate --feature-dir <feature-dir> --expected-revision <revision> --format json}}`
only after the independent audit is accepted and all blocking gaps are
resolved. The only honest outcomes are
`complete_against_frozen_scope`, `qualified_with_declared_gaps`, `blocked`, or
`stale`. Never claim `absolutely_complete`; scope-relative completeness requires
a frozen denominator, bidirectional traceability, explicit exclusions and gap
dispositions, usable materials, and an accepted independent audit.

Only a non-stale validated package may run
`{{specify-subcmd:specify-runtime test-design handoff --feature-dir <feature-dir> --expected-revision <revision> --format json}}`.
The runtime creates the pointer-only handoff to Tasks, including canonical
artifact refs, `test_case_refs`, `test_data_refs`, gap ref, audit ref, source
fingerprint, and claim status. Do not copy the catalog or data manifest into
the handoff.

For a Tasks consumer, preserve the exact lifecycle `validate -> handoff ->
publish -> projection-build --consumer tasks -> projection-verify`. Because
`handoff` increments state revision, rerun `status` after handoff and publish
with that new handed-off revision. Plan and Quick may publish/build directly
from validated state; Review and Tasks are feature-only consumers. Publish with
`{{specify-subcmd:specify-runtime test-design publish --feature-dir <feature-dir> --expected-revision <revision> --format json}}`,
omitting `--feature-dir` for project scope. The runtime alone writes the
content-addressed publication. For feature scope, run
`{{specify-subcmd:specify-runtime test-design projection-build --feature-dir <feature-dir> --consumer <plan|quick|tasks|review> --basis-ref <project-relative-ref> --obligation-ids <TO-001,TO-002> --format json}}`;
for project scope omit `--feature-dir` and allow only `plan|quick`. Project
Tasks or Review projection is invalid. Omit `--obligation-ids` only for the
complete applicable denominator. Verify the returned pointer with
`{{specify-subcmd:specify-runtime test-design projection-verify --feature-dir <feature-dir> --projection-ref <project-relative-ref> --expected-sha256 <sha256> --format json}}`,
omitting `--feature-dir` only for a project Plan/Quick projection. Publications and projections
are runtime-owned canonical artifacts. A projection is typed and pointer-only;
it never copies catalog, data, coverage, gap, or audit bodies, and neither the
producer nor a consumer patches it. A later feature `handoff` is legal, but its
revision increment invalidates every earlier publication and projection; rerun
`status`, `publish`, `projection-build`, and `projection-verify` before further
consumption.

Use an immutable upstream consumer basis: Plan uses the current feature
`spec-contract.json`; Quick uses the runtime-owned
`.planning/quick/<id>/confirmation.json`; Tasks uses the finalized
`plan-contract.json`; Review uses `implementation-handoff.json`. Never use the
consumer artifact that will receive `projection_binding` as its own basis.

This invocation authorizes only this planning-only test-design workflow. It does
not make the code map dirty and requires no project-cognition closeout. Report
the frozen scope, claim status, material readiness, unresolved gaps,
publication, built projection refs, and compatibility handoff path. Stop at the
selected consumer boundary; in the default formal path recommend `$spx-tasks`
without invoking it in the same run.
