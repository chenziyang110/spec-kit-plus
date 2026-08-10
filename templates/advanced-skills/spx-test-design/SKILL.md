---
name: spx-test-design
description: Planning-only test intelligence workflow for advanced coding models. Use when a project or planned feature needs a frozen test universe, traceable professional test cases, explicit test-data decisions, an independent coverage audit, or a fresh handoff before task generation.
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
independent audit, validation, and the final handoff.

## Select and freeze the run

Select exactly one mode:

- `project-baseline`: scan a declared project boundary and use
  `.specify/test-design/`.
- `feature`: design from a validated feature plan and use
  `<FEATURE_DIR>/test-design/`.
- `incremental-update`: CAS-reenter an existing root against an explicit source
  delta while preserving semantically unchanged stable IDs.
- `audit`: CAS-reenter an existing package for assessment without expanding its
  frozen boundary.

For feature-scoped work, resolve the feature in paths-only mode, run
`{{specify-subcmd:specify-runtime workflow show --feature-dir <feature-dir> --format json}}`,
and require current planning truth. The expected workflow owner remains `plan`;
never edit `FEATURE_DIR/workflow.json` or transition the required stage.
`$spx-test-design` is optional between `$spx-plan` and `$spx-tasks`, not a
replacement for either stage.

Before discovery, freeze the query, source refs, included and excluded paths,
risk dimensions, and runtime-computed fingerprint. Include the applicable
capabilities, requirements, entrypoints, environments, operational risks, and
UI surfaces. Do not claim coverage outside that denominator. Initialize through
one of these runtime-owned forms, passing the frozen input as JSON:

```text
{{specify-subcmd:specify-runtime test-design init --scope project --mode project-baseline --leader-id <leader-id> --input-json <json> --format json}}
{{specify-subcmd:specify-runtime test-design init --scope feature --mode feature --feature-dir <feature-dir> --leader-id <leader-id> --input-json <json> --format json}}
```

On resume, run
`{{specify-subcmd:specify-runtime test-design status --feature-dir <feature-dir> --format json}}`
(omit `--feature-dir` for project scope) and continue from its phase, revision,
accepted results, blockers, and source fingerprint; never reconstruct state
from chat or overwrite runtime-owned state files. Reenter an existing root only
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

## Audit, validate, and hand off

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

This invocation authorizes only this planning-only test-design workflow. It does
not make the code map dirty and requires no project-cognition closeout. Report
the frozen scope, claim status, material readiness, unresolved gaps, and handoff
path. Stop and recommend `$spx-tasks`; do not invoke it in the same run.
