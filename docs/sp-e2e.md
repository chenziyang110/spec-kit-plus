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

After the branch's installation/catalog integration is completed, use the
integration-native surface: `$sp-e2e` for Codex, `/sp-e2e` for Claude,
`/skill:sp-e2e` for Kimi, or `/sp.e2e` for command-based integrations. The
Advanced counterpart is `spx-e2e`. These are agent workflows, not new
`specify` or `specify-runtime` subcommands.

```text
$sp-e2e Test the desktop client's file rename operation. First derive normal,
invalid/boundary, external deletion/rename/replacement, timing, permission,
conflict, duplicate/cancel/retry, recovery and cross-view consistency scenarios.
Use available visual interaction tools and independent filesystem readback.
Keep untestable scenarios visible; do not require a browser automation harness.
```

An unqualified full-product request must not silently become a changed-files
run. Feature-only and regression scopes remain explicitly narrower claims.

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
