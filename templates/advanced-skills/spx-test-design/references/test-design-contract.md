# Test Design Contract

## Authority and roots

The test-design runtime owns lifecycle state, lane manifests and results, gap
state, validation, publication, projection, and handoff generation. The artifact runtime owns mutation
of the four canonical design artifacts. Read them with `artifact show`; create
them only through test-design initialization or their registered scaffolds and
update them only through fresh leased JSON-pointer `artifact patch` operations.
Never direct-write, whole-file submit, or model-reconstruct a canonical JSON
artifact.

| Mode | Scope root | Entry condition | Preservation rule |
| --- | --- | --- | --- |
| `project-baseline` | `.specify/test-design/` | declared repository boundary | establish the first frozen denominator |
| `feature` | `<FEATURE_DIR>/test-design/` | explicit feature boundary and current authoritative sources | bind cases to selected feature obligations and consumer bases |
| `incremental-update` | existing matching root | explicit source delta and current runtime revision | retain stable IDs for semantically unchanged rows |
| `audit` | existing matching root | package, original denominator, and current runtime revision exist | report findings; do not expand scope |

Test Design is an independent producer and does not require a completed Plan.
Feature mode may use a current specification or Plan as intended-behavior input,
but current code is final authority for implemented behavior; tests,
configuration, official contracts, and live runtime evidence corroborate it.
Project Cognition only navigates to those sources and no cognition claim may
replace code verification. If
a feature workflow exists, query it with
`{{specify-subcmd:specify-runtime workflow show --feature-dir <feature-dir> --format json}}`
for source and consumer context but do not mutate or advance it. Project mode
does not invent a feature directory or feature workflow.

For ordinary resume, query `test-design status` and follow its exact next argv.
Only `init --mode incremental-update|audit --expected-revision <revision>` may
reenter an existing root. The runtime must compare-and-swap the revision,
preserve canonical artifacts and their semantically unchanged IDs, archive and
invalidate any stale derived handoff, and reset lane, audit, validation, and
claim state for a fresh lifecycle. Never simulate reentry with direct writes.
Incremental update may freeze an explicit source delta; audit must keep source
refs, included and excluded paths, and risk dimensions identical to the
existing denominator while the runtime fingerprints their current content. A
CAS mismatch is a blocked resume, not permission to overwrite.

The canonical root contains:

- `test-state.json`: runtime revision, phase, fingerprint, lanes, audit, and
  claim status.
- `test-universe.json`: `CAP-*` capabilities, `SCN-*` scenarios, and the
  proposed `TC-*` inventory.
- `test-catalog.json`: professional, executable-or-reviewable case definitions.
- `test-data-manifest.json`: `TD-*` datasets, disposition, readiness,
  provenance, and hygiene.
- `coverage-matrix.json`: `COV-*` bidirectional traceability rows.
- `test-gaps.json`: `GAP-*` omissions, residual risks, owners, next actions,
  and observable unblock criteria.
- `lane-manifest.json` and `lane-results/`: runtime-owned bounded discovery and
  audit records.
- `handoff-to-tasks.json`: runtime-generated pointer-only downstream contract.
- publication: runtime-generated, content-addressed canonical package.
- projections: runtime-generated typed pointer-only selections for `plan`,
  `quick`, `tasks`, or `review`, each bound to a basis ref and SHA-256.

## Frozen denominator

Freeze before discovery:

- the user's query and selected mode;
- authoritative source refs and the runtime-computed source fingerprint;
- included and excluded paths;
- applicable requirements, capabilities, acceptance criteria, official
  entrypoints, environments, integrations, and operational boundaries;
- relevant risk dimensions, including positive, negative, boundary, state,
  permission, failure, recovery, concurrency, compatibility, security,
  performance, accessibility, and observability concerns;
- applicable UI obligations such as responsive behavior and visual fidelity,
  expressed through the appropriate risk dimensions and bound to inspectable
  UI or visual-comparison evidence rather than treated as new canonical risk
  dimensions.

Use only applicable dimensions, but every omitted dimension needs a reason.
Changing a source ref, boundary, exclusion, risk dimension, or acceptance owner
stales the prior validation and requires CAS reentry in `incremental-update`
mode. Never impersonate the runtime reset by overwriting the existing root.

## Case quality and traceability

Every `TC-*` row must answer:

1. Which requirement, capability, `SCN-*`, acceptance item, and `COV-*` row
   does it cover?
2. What risk or behavior does it distinguish from nearby cases?
3. What are its priority, lifecycle stage, preconditions, and data needs?
4. What action or observation occurs, and what deterministic oracle proves the
   expected result?
5. Which command check, rule check, manual observation, visual comparison, or
   runtime diagnostic supplies the required evidence?
6. At which downstream task or shared verification gate can it be realized?

Do not multiply cases by rote combinations. Use equivalence partitions,
boundaries, state transitions, decision/rule coverage, threat and failure
models, and representative pairwise combinations where they sharpen the
denominator. Preserve one stable ID for one stable semantic obligation; split
or retire an ID only when its meaning changes.

Forward coverage maps each frozen obligation to one or more cases or a declared
gap. Reverse coverage maps every case to an in-scope obligation and every data
record to at least one case and scenario. A `covered` row needs planned evidence
or acceptance evidence; prose confidence is not evidence.

Every `GAP-*` row has non-empty `affected_obligation_refs`, every referenced
`TO-*` points back through `gap_refs`, and exclusions, deferrals, waivers, and
blocking dispositions remain consistent on both sides.

## Materials contract

Every `TD-*` dataset has exactly one resolution disposition:

- `reuse`: cite at least one provenance ref and mark ready.
- `generate`: provide a deterministic generation recipe and mark ready or
  recipe-ready.
- `search`: state the target and evidence criteria; remain evidence-needed
  until a safe source is bound.
- `request`: give self-contained request instructions and observable unblock
  criteria; mark human-input-required.
- `block`: record the exact blocker and unblock criteria.
- `defer`: record the reason, residual risk, owner, and later unblock criteria.

Also record kind, sensitivity, PII flag, source, applicable cases/scenarios,
classification reason, sanitization status, and retention policy. Do not embed
secrets, credentials, production tokens, unsanitized personal data, licensed
material without permission, or mutable remote content without a pinned
provenance record. Search is evidence acquisition, not permission to import.
Request the smallest safe sample when a human boundary is real.

Search proposals remain untrusted until the Leader checks source authority,
licensing, reproducibility, sanitization, and provenance. The Leader registers
accepted inline text/JSON with `specify-runtime evidence register` and imports
accepted external or binary files with `specify-runtime evidence import`, always
using `scope: test-design` plus explicit source and provenance. Cite the returned
content-addressed `evidence_id` or `record_ref`; a worker cannot register its own
proposal as accepted truth.

Route missing external feasibility, normative oracles, disposable proofs, and
evidence beyond bounded read-only search to `$spx-deep-research`. Preserve the
affected coverage/gap refs, then resume only from its primary-source evidence
and `Planning Handoff`. If that handoff changes the frozen inputs, use
revision-guarded `incremental-update` rather than patching lifecycle state.
After verifying the handoff, the Leader registers or imports the accepted
object under evidence scope `test-design`, preserving the Deep Research record
and Planning Handoff in provenance. Canonical rows cite that new Test Design
record ref because the runtime rejects evidence from an unrelated scope.

## Completion gate

Validation may emit:

- `complete_against_frozen_scope`: every applicable frozen obligation is
  covered, every case has a viable oracle and evidence route, every referenced
  dataset is ready or recipe-ready, traceability is bidirectional, and the
  independent audit has no unresolved blocking finding.
- `qualified_with_declared_gaps`: the package is usable, but every remaining
  non-blocking omission has a `GAP-*` record, owner, residual risk, disposition,
  next action, and unblock criteria.
- `blocked`: a blocking gap, unsafe material, missing authority, or unusable
  oracle prevents a truthful handoff.
- `stale`: the frozen sources or boundary no longer match the validated
  fingerprint.

Never use totalizing claims. The package can prove only completeness against
its frozen denominator. Validation failure remains a typed blocker and follows
`references/blocker-resolution.md`; do not relabel it as a warning.

## Publication and downstream boundary

After validation, call `specify-runtime test-design publish` with the current
revision. Build only explicitly selected consumer views with
`specify-runtime test-design projection-build --consumer plan|quick|tasks|review
--basis-ref <project-relative-ref>` and optional obligation IDs, then verify each
returned ref and digest with `specify-runtime test-design projection-verify`.
Project scope omits `--feature-dir` and supports only Plan or Quick projections;
Tasks and Review projections are feature-only. Publications and projections are
runtime-owned; no workflow patches them. A projection contains typed pointers
and selection metadata, not copied canonical bodies.

Tasks has one stricter compatibility sequence: `validate -> handoff -> publish
-> projection-build --consumer tasks -> projection-verify`. Since `handoff`
increments revision, publish must bind the new handed-off revision. Plan, Quick,
and a feature-scoped Review publish/build directly from validated state. Never call `handoff`
after publish because it makes that publication stale.

The compatibility handoff to `$spx-tasks` contains refs, not duplicated content. Tasks bind
the relevant `test_case_refs` and `test_data_refs` to task-local contracts and
shared gates. Implement realizes fixtures and tests; Review executes integrated
verification and checks fresh evidence. Test Design does neither. A later source
or basis change invalidates the affected handoff or projection until an
incremental update validates a new fingerprint and the runtime republishes and
rebuilds the consumer view.
