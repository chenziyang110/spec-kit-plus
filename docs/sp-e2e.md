# Scenario-first E2E and coverage accounting

`sp-e2e` first performs systematic test analysis and design, then executes real
product scenarios through available visual-model interaction, auxiliary tools,
or a suitable existing runner. Desktop/mobile clients, web, CLI and service
projects are equal subjects. Executable test files are optional implementation
assets, not a prerequisite for discovering or visually executing client tests.
`sp-test-design` remains the independent planning-only producer; E2E consumes
its current publications read-only when present. E2E does not replace integrated
Review, visual comparison or human Accept.

Start with [scenario derivation, the rename example and visual trace contracts](sp-e2e-scenarios.md).
The combination/native helper sections below apply only to that selected lane.
An explicit planning-only request returns the scenario book without an execution
claim; otherwise proceed through feasible real execution and retain blockers.

## Invocation

Use the integration-native surface: `$sp-e2e` for Codex, `/sp-e2e` for Claude,
`/skill:sp-e2e` for Kimi, or `/sp.e2e` for command-based integrations. The
Advanced counterpart is `spx-e2e`. These agent workflows use the Go
`specify-runtime e2e` task/acceptance owner; there is no Python `specify e2e`
state writer and no E2E execution Activity enum.

```text
$sp-e2e Test the desktop client's file rename operation. First derive normal,
invalid/boundary, external deletion/rename/replacement, timing, permission,
conflict, duplicate/cancel/retry, recovery and cross-view consistency scenarios.
Use available visual interaction tools and independent filesystem readback.
Keep untestable scenarios visible; do not require a browser automation harness.
```

An unqualified full-product request must not silently become a changed-files
run. Feature-only and regression scopes remain explicitly narrower claims.

## Seven stages with verified producer/consumer handoffs

Both profiles use the same seven-stage protocol. The first action is to establish
the actual product, declared targets and source-backed operation inventory.
Selecting Playwright, launching a browser or copying existing tests cannot
establish what the whole project needs.

| Stage | Consumes | Required output | Independent acceptance before consumption |
| --- | --- | --- | --- |
| 1. Scope, inventory and capabilities | Original request, requirements and actual entrypoints | Stable requirement/operation IDs, assumptions, cross-feature dependencies, target/build/OS/device matrix, capability probes and discovery gaps | Reconcile the original request and live product surfaces, including unknown/unread areas; check every declared target. |
| 2. Scenario design | Accepted stage 1 inventory and source contracts | Frozen schema-v2 scenario book; explicit conditions, boundary units, event/checkpoint obligations, oracles and exclusions; derive/check reports | Challenge semantic completeness and expected outcomes; rerun `derive/check --require-v2`; preserve the full parent denominator for scoped books. |
| 3. Execution readiness | Accepted inventory and scenario book | Exact route, build and launch identity; authorized accounts/fixtures; setup, readback and reset probes; runner bindings/collection where selected | Reproduce decisive readiness probes and verify every required observation channel. Missing tools or fixtures block the affected cases. |
| 4. Product execution | Accepted book and current readiness for the exact scope/target | Immutable runs with original actions, captures, independent effects, attempts, cleanup, trace and selected native reports/audits | Reconcile every scenario ID and assertion to inspectable evidence; verify actual target, current hashes and decisive observations. |
| 5. Repair and regression | Run evidence, failed/rejected rows and blocker causes | Causal defect/repair record, owner, affected IDs, changed versions and fresh regression evidence | Reproduce the original failure against the correction and check affected journeys. E2E repairs owned test assets; product fixes return to their owner. |
| 6. Independent reconciliation | Original request, complete ledger, all accepted artifacts and all attempts/lane audits | Per-row audit, set differences from requested scope to clean passes, missing coverage, exclusions and required rework | Check discovery, oracle adequacy, each target and every selected lane. New omissions reopen the earliest affected stage. |
| 7. Truthful report and closeout | Independent audit, exact artifact versions and final ledger | Reproducible report separating design, execution, outcomes, combination coverage and visual acceptance; all unresolved IDs and resume points | Compare the report with every requested item and integrated journey. An unresolved mandatory row prevents a full-scope success claim. |

Each stage uses bounded execution workers and a separate read-only validator
subagent. The leader accepts only after the validator checks the original
request, full acceptance set, actual artifacts and original evidence. The
validator must not be the author of that artifact revision. A later stage's
packet carries the accepted upstream record and exact output version/digest;
it does not consume the sentence “A is done.”

Freeze the complete contract through the Go E2E owner. A
`tests/e2e/workflow-ledger.md` or equivalent test ledger can index its records;
it does not authorize task transitions. Each task records stable ID, stage, scope IDs, dependencies, worker,
validator, input/output refs and digests, acceptance rows, reproduction
commands/manual steps, environment/preconditions, expected and actual outcomes,
evidence, status, gaps and next action. Keep immutable submission/review
snapshots; the ledger is a mutable index. Track
`pending -> running -> submitted -> verified -> accepted`; retain rejected
and blocked work instead of checking it off. Existing packet/artifact/runtime
owners remain authoritative where they apply.

For example, if A has ten required outputs and delivers six, the validator
returns the four unmet rows, A remains unaccepted, and B stays blocked on A.
The worker repairs A, a different validator checks the new artifact, and the
leader accepts that exact revision before dispatching B. Independent ready
work can continue in isolated namespaces. If B later disproves A's basis,
reopen A and invalidate affected descendant acceptance, then revalidate from
that point.

Accepting a complete failed-run report means its evidence is usable for repair
and diagnosis; it does not mean the product passed. Audit/reporting may read
blocked or rejected records to explain partial results without unlocking their
dependents. An explicit planning-only request goes from accepted design to
design audit/reporting and makes no execution claim. Without independent
validation capability, safe drafting and self-checking may continue, but
independent acceptance stays blocked.

## Runtime-enforced handoffs

The Go owner stores versioned state and immutable, content-addressed snapshots
under `.planning/e2e/<run-id>/`. Each bound input, output and evidence file also
has an `archive_ref` in `blobs/<raw-sha256>.bin`, preserving its actual bytes
when a later attempt reuses the original path. History is not just a list of
hashes. `artifact show/list` can inspect those records; raw binary full views
use bounded base64 rather than lossy text. Generic artifact mutation and every
generic result destination are excluded from this owned tree. Scenario books,
traces, helper audits and native reports remain ordinary
test assets. Do not add workflow lifecycle fields to their existing schemas.

Both profiles begin with a bounded capability negotiation through the installed
project launcher. The executable name below denotes that resolved launcher:

```sh
specify-runtime api ensure --capabilities e2e.init,e2e.status,e2e.scope-add,e2e.task-start,e2e.task-submit,e2e.review-start,e2e.review-submit,e2e.task-accept,e2e.reopen,e2e.close --format json
specify-runtime api pack --capabilities e2e.init,e2e.scope-add,e2e.task-submit,e2e.review-submit --include-schema --format json
```

Missing capabilities are an explicit upgrade blocker. Installation handshake
checks reject a binary that lacks the new operations. Initialization still
preserves its existing best-effort installation/recovery behavior; an old
binary or old markdown DONE mark cannot grant E2E acceptance.

| Operation | Input and result |
| --- | --- |
| `e2e init` | Freeze `e2e-plan-input`, leader identity, execution/planning mode, requested scope, seven-stage task placeholders, acceptance criteria, input/output paths, dependencies and exclusive resources. Future output files need not exist. |
| `e2e status` | Re-read the full denominator, current revision, unresolved work, snapshot and byte freshness, and exact continuation. This query does not rewrite state. |
| `e2e scope-add` | Add discovered scope/tasks with a reason and evidence. Retain old requirements and reopen affected work; never delete a platform to turn the result green. |
| `e2e task-start` | Check exact accepted prerequisites and required successful outcomes, freeze current inputs, refuse conflicting active outputs/resources, and return a WorkerTaskPacket, attempt and submission template. Native agent tools dispatch the worker. |
| `e2e task-submit` | Bind the worker to its packet; require every scope/acceptance pair, actual/expected result, preconditions, reproduction and raw evidence; retain an immutable submission containing the normalized WorkerTaskResult. |
| `e2e review-start` | Bind another recorded identity to the exact submission, original task and complete row set; return the independent review packet/template. |
| `e2e review-submit` | Require every review row and fresh evidence; retain inspected/replayed methods and rejection evidence. Editing the output requires a new author submission and another reviewer. |
| `e2e task-accept` | Let the fixed leader accept only the current completely verified revision. Complete failed-run reports remain failed observations. |
| `e2e reopen` | Record drift or counterevidence, retain old attempts/reviews, and invalidate the affected producer and all descendants. |
| `e2e close` | Recheck all required scopes/stages and the entire evidence chain before a scoped result. Planning completion, a complete failure report and product execution success are distinct. |

A terminal closeout (`blocked`, `reported`, `complete` or `planning-complete`)
closes ordinary task/review/accept transitions. Read current `e2e status` and have
the leader explicitly call `e2e reopen` for the earliest affected task with the
current revision, recovery reason and evidence. For blocked/reported runs,
`next_argv` supplies the earliest unresolved or nonpassing task and placeholders
for the actual recovery reason/evidence; passing terminal runs supply no
ordinary next action. The runtime preserves prior closeout and attempt/review
history, returns a fresh revision, and invalidates the reopened task and affected
descendants for revalidation. Existing source-drift invalidation and `scope-add`
expansion can still reopen the run.

All mutations after initialization use the current `--expected-revision` from
runtime output. After a conflict, read status and decide the correct next
action; do not blindly retry the old argv. Semantic JSON inputs use documented
inline JSON, project-contained `@path`, or stdin. Fill the returned worker and
review templates instead of reconstructing runtime state or receipt hashes.
Both start operations return `worker_task_packet`, consumable by the existing
shared `WorkerTaskPacket` parser, plus `worker_task_packet_binding` identifying
the immutable envelope digest and `/worker_task_packet` JSON pointer. Preserve
the outer E2E contract, target, attempt and dependency bindings alongside that
view. A worker result's `packet_id` is the enclosing packet digest; the shared
packet schema is not extended with a competing lifecycle or a made-up feature.
Execution views include the complete intent/context contract required by
`validate_worker_task_packet`. Review consumers explicitly select
`validate_worker_task_packet(packet, read_only_review=True)`: the same intent,
context and acceptance gates apply, but the reviewer must have no write scope
or produced artifacts. Default execution validation still requires owned
outputs. The packet also references an immutable original task contract, so
tasks with no additional file inputs remain independently interpretable.

Preserve the original request as a test-document input. The plan must name
every declared target/operation and include required criteria for cross-feature
journeys, each selected visual/native/combination lane, cleanup and final
reconciliation. `require: accepted` allows a complete factual report as input;
`require: passed` additionally requires the producer's tested outcome to pass.
Any declared producer output consumed as another task's input must have a
dependency path, even across different target scopes. Conflicting active reads
and writes are blocked. A passing submission cannot include failed validation
rows or a nonzero native runner exit code, even if its outer status says pass.
Resource exclusions apply to declared resources in a run; coordinate separate
runs through the existing Work Board and their actual shared resources.

For an incomplete upstream, stages 6/7 may explicitly start in `--diagnostic`
mode to report gaps without treating those inputs as accepted prerequisites.
Diagnostic observations cannot become passing execution evidence. A report with
unaccepted mandatory tasks leaves the run blocked. After report acceptance,
`close --outcome pass|failed|blocked` still checks the whole requested contract;
the caller cannot manufacture success by choosing `pass`.

The checks enforce structural consistency and version bindings. Distinct
`worker-id`, `validator-id` and `leader-id` strings are **not authentication** of
native agent processes. Actually dispatch separate agents and retain their
records. Hashes cannot prove a screenshot is authentic, that an agent replayed
a command, that an oracle is correct, or that initial product discovery was
complete. Those remain independent semantic-review obligations. The Python
helpers add lane-specific accounting, not an attestation of product truth.

## Platform-specific readiness under a shared process

Use the seven stages for web, Windows/Linux/macOS desktop, iOS/iPadOS, Android,
CLI/service and other software, while establishing the real execution route
for each declared target. Record browser/OS/device versions, actual build and
installation identity, entrypoint, accounts, services, capture/inspection,
interaction, independent effect readback and fixture reset capabilities.

A webview in a browser does not prove its native desktop shell. An iOS
simulator result does not prove a physical iPhone result. An Android emulator
does not establish another device/OS target. A CLI, service, library, extension
or device uses its actual consumer program, host or protocol instead of a
forced UI. Missing capabilities remain target-specific blockers in the full
scope; do not silently relabel the target not-applicable.

The supplied native wrapper supports serial pytest and local Playwright Test.
Other platforms can use working visual/control tools, an existing validated
adapter or an explicit human route. Method coverage across platforms is
separate from having executed and verified every platform in this environment.

Keep hashes of fixture definitions, seed inputs and setup scripts separate from
run evidence for temporary objects that tests intentionally rename/delete.
When the scenario book changes, its entire `book_sha256` binding changes:
obtain fresh evidence for that book, retaining old runs as history. Do not
transplant old passing observations into the new trace. Independently scoped
books prepared before execution may retain their own unchanged evidence; this
is not native shard merging.

## What prevents omissions

Discover intended requirements and actual entrypoints independently of existing
tests. Challenge each operation's assumptions and account for input, state,
external events, exact timing, recovery and side effects before selecting cases.
Keep unknown surfaces and source/requirement disagreements as discovery gaps.
Separate requirements discovered, scenarios designed, scenarios executed and
outcomes actually observed. Applicable cases without tools remain blocked, not
not-applicable. See `e2e_scenarios.py catalog`, `schema`, `derive`, `check` and
`audit` for the standard question set, exact field shapes and declared-accounting
checks. A visual trace needs no pytest result or executable test reference.

After discovery, the shared combination helper derives feasible t-way
interactions, constructs a deterministic covering array and recomputes that
denominator when auditing native results. It rejects unmapped requirements,
impossible mandatory combinations, unreachable factor values, misspelled fields
and budgets requiring silent sampling. Ordinary matrices may use pairwise;
critical bounded matrices may use higher strength or exhaustive enumeration.
Known high-risk combinations remain mandatory. Ordered events are distinct
scenarios, not something parameter pairwise coverage proves.

A negative action the product must reject is a test obligation, not an
infeasible configuration. Missing infrastructure, skipped cases, quarantine,
fail-then-pass retries and unavailable shards remain gaps rather than exclusions.
No checker infers product truth from a green process exit alone.

## Combination helper (optional automation lane)

The implementation is `scripts/shared/e2e_coverage.py`, requiring Python 3.11+
and no third-party packages. Existing `scripts/shared` package inclusion covers
the source location; installed-project copying still needs integration testing.
Run from a source checkout:

```text
python scripts/shared/e2e_coverage.py plan tests/e2e/coverage-manifest.json --root .
python scripts/shared/e2e_coverage.py audit tests/e2e/coverage-manifest.json --root . --results test-results/e2e/run-001/results.json
```

Generated projects use `.specify/scripts/shared/e2e_coverage.py` instead.
The helper emits JSON and never executes commands, changes application files or
writes runtime state. Preserve output in a new run directory; never overwrite
old evidence. Its contract is unchanged by the visual/scenario lane.

| Exit | Meaning |
| --- | --- |
| 0 from `plan` | A planned case set for the declared model; no execution claim. |
| 0 from `audit` | Every planned case passed with consistent source/test/evidence bindings and a successful original runner. |
| 1 | Incomplete execution, including missing, failed, skipped, blocked or flaky cases. |
| 2 | Invalid model/input, missing evidence, stale hashes or exceeded budgets. |

Defaults bound enumeration to 10,000 candidates per journey, 50,000 across a
manifest, 100,000 row-interaction work units per journey and 1,000 selected
cases. `--max-cases` may explicitly raise the selected-case budget, never lower
strength. Partition large products while preserving cross-feature obligations.
The greedy algorithm is deterministic, not a minimum-case-count guarantee.

## Combination manifest contract

This is an illustrative shape, not executable evidence. Replace source revision,
paths and SHA-256 values with actual project data.

```json
{
  "schema_version": 1,
  "scope": "order submission in a local sandbox",
  "source_revision": "actual-source-revision",
  "sources": [{"path": "src/orders.ts", "sha256": "actual-64-character-lowercase-sha256"}],
  "exclusions": [{"scope": "real bank settlement", "reason": "sandbox only", "owner": "payments"}],
  "requirements": [{"id": "ORDER-1", "source": "spec.md#order-creation", "assertion": "Exactly one order is persisted after a valid submission."}],
  "journeys": [{
    "id": "order-submit",
    "requirements": ["ORDER-1"],
    "steps": ["sign in", "fill order", "submit", "reload and independently verify persisted order", "clean up"],
    "factors": {
      "role": ["customer", "admin"],
      "browser": ["chromium", "firefox"],
      "dataset": ["one-item", "many-items"]
    },
    "strength": 2,
    "exclude": [],
    "mandatory": [{"role": "customer", "browser": "firefox", "dataset": "many-items"}]
  }]
}
```

`strength` is a positive integer up to the factor count, or `"exhaustive"`.
A constraint is `{ "when": { "factor": "value" }, "reason": "evidence-backed infeasibility" }`.
Mandatory combinations are nonempty partial assignments; factor values are
distinct strings. Every requirement maps to a journey; a passed case asserts
all that journey's requirements. Split success and denial/error paths when
oracles differ. Repeated steps, such as submit -> submit, are allowed.

The planner returns manifest_sha256, stable E2E-* IDs, parameter rows,
requirement mappings, journey denominators and exclusions. Reconcile every
selected variant into cards or executable tests. The scenario checker does not
compute t-way coverage. Hash all relevant source/contract/config/fixture files;
the helper cannot detect an important source omitted from `sources`.

## Actual native runner results

For supported serial pytest/Playwright Test use the supplied
[native execution wrapper](sp-e2e-runner.md). Other harnesses need a validated
adapter that compares full collected IDs, preserves original attempts/reports
and never turns a plan into passing results. Visual-model observations belong
in the scenario trace, not fabricated pytest/Playwright output.

Native results require schema_version 1, exact manifest_sha256, matching
source_revision, actual run_id/target, timezone-aware started_at/finished_at,
actual command argv and exit_code, nonempty test_sources/run-level evidence
arrays of `{path, sha256}`, and cases. Case statuses are passed, failed, skipped,
blocked, not_run or flaky. A passed case additionally binds test_ref to a hashed
test source, asserted_requirements to the exact plan and nonempty hashed
evidence. Retain retries; fail-then-pass is flaky. Unexpected/duplicate IDs are
invalid; omitted IDs become not_run.

File hashes bind current project-contained source/test/evidence bytes. Absolute
paths, parent traversal and symlink escapes are rejected. Manifest/source/test/
evidence drift invalidates old results. No unexecuted case disappears from the
denominator. Native reports separate requirements, statuses, t-way interactions,
missing mandatory combinations and runner exit status. A visual/scenario trace
cannot override a failed native audit or certify partial shards as complete.

## Limits and integration readiness

`complete_against_frozen_scope` is a bounded combination-model/evidence
consistency claim. `scenario_design_ready` is design accounting only;
`evidence_complete_against_declared_scenarios` is trace consistency only. None
attests complete discovery, truthful reporting, adequate assertions, the actual
binary executed, pixel inspection, UI acceptance or release safety. Preserve
independent inventory/assertion/evidence review and visible qualifications;
missing visual comparison remains pending-human-review.

The branch's merge gates and outstanding catalog/installation work are recorded
in [E2E readiness](../plans/sp-e2e-readiness.md). Until closed, this is a draft
implementation, not an installed/released workflow guarantee.
