# E2E execution and coverage accounting

`sp-e2e` is an execution workflow: inventory the selected product boundary,
implement missing E2E tests, run the real system, and account for every required
case. `sp-test-design` remains the independent planning-only producer. E2E does
not replace integrated Review, visual comparison, or human Accept.

## Invocation

After the branch's installation/catalog integration is completed, use the
integration-native surface: `$sp-e2e` for Codex, `/sp-e2e` for Claude,
`/skill:sp-e2e` for Kimi, or `/sp.e2e` for command-based integrations. The
Advanced counterpart is `spx-e2e`. These are agent workflows, not new
`specify` or `specify-runtime` subcommands.

For example:

```text
$sp-e2e Run the complete order-management product in the local sandbox.
Include customer/admin roles, tenant boundaries, lifecycle transitions,
empty/large/invalid data, retry/duplicate submission, and browser combinations.
List every uncovered feature or unexecuted combination; do not run only smoke tests.
```

An unqualified full-product request must not silently become a changed-files
run. Feature-only and regression scopes remain explicitly narrower claims.

## What prevents omissions

Discover intended requirements and actual entrypoints independently of existing
tests. Freeze stable requirement IDs, complete business journeys, source hashes,
factors, constraints, and scope exclusions before selecting a case set. Keep
unknown surfaces and source/requirement disagreements as gaps. Separate
requirement discovery from whether tests were planned, executed, or passed.

The shared Python helper derives feasible t-way interactions, constructs a
deterministic covering array, and independently recomputes that denominator
when auditing results. It rejects unmapped requirements, impossible mandatory
combinations, unreachable factor values, misspelled fields, and budgets that
would require silent sampling. Ordinary matrices may use pairwise coverage;
critical bounded matrices can use higher strength or full enumeration. Known
risk combinations remain mandatory even when pairwise would not choose them.
Ordered events such as retry-after-timeout are separate journeys, not something
pairwise factors can prove.

A negative action that the application must reject is a test obligation, not an
infeasible combination. Missing infrastructure, skipped cases, quarantine,
fail-then-pass retries, and unavailable shards remain gaps rather than exclusions.
The checker does not infer truth from a green process exit alone.

## Shared helper

The implementation is `scripts/shared/e2e_coverage.py`, requiring Python 3.11+
and no third-party packages. Existing `scripts/shared` package inclusion covers
the source location; installed-project copying still needs integration testing.
Run from a source checkout:

```text
python scripts/shared/e2e_coverage.py plan tests/e2e/coverage-manifest.json --root .
python scripts/shared/e2e_coverage.py audit tests/e2e/coverage-manifest.json --root . --results test-results/e2e/run-001/results.json
```

Generated projects use `.specify/scripts/shared/e2e_coverage.py` instead.
The helper emits JSON to stdout and never executes commands, changes application
files, or writes runtime workflow state. Save successful output into a new
run-specific directory. Preserve old evidence rather than overwriting it.

| Exit | Meaning |
| --- | --- |
| 0 from `plan` | A complete planned case set for the declared model; no execution claim. |
| 0 from `audit` | Every planned case passed with consistent source/test/evidence bindings and a successful original runner. |
| 1 | Incomplete execution, including missing, failed, skipped, blocked, or flaky cases. |
| 2 | Invalid model/input, missing evidence, stale hashes, or exceeded budgets. |

Defaults bound enumeration to 10,000 candidate rows per journey, 50,000 across
a manifest, 100,000 row-interaction work units per journey, and 1,000 selected
cases. `--max-cases` may explicitly raise the selected-case budget; it never
changes interaction strength. A larger product should partition independent
journeys while preserving cross-feature obligations. This greedy algorithm is
deterministic, not a guarantee of the smallest possible case set.

## Manifest contract

This is an illustrative shape, not executable evidence; replace the source
revision, paths, and SHA-256 values with actual project data.

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
An exclusion is `{ "when": { "factor": "value" }, "reason": "evidence-backed infeasibility" }`.
A mandatory combination is a nonempty partial factor assignment. All factor
values are distinct strings. Every requirement must be referenced by a journey;
every passed case must assert every requirement referenced by that journey.
Split success and denial/error paths when their oracles differ. Repeated journey
steps are allowed, for example submit -> submit -> verify idempotence.

The planner returns `manifest_sha256`, stable `E2E-*` IDs, exact parameter rows,
requirement mappings, per-journey denominators, and visible scope exclusions.
Hash all relevant source/contract/configuration/fixture files; the helper cannot
detect an important source file omitted from `sources`.

## Actual runner results

Implement a deterministic adapter for the project's existing runner. It must
compare collected IDs with the planned IDs, retain original reports and all
attempts, and normalize their outcomes. No adapter may turn a plan into passing
results. The helper itself is not a browser runner or a trusted reporter.

The result object requires `schema_version: 1`, the exact `manifest_sha256`,
matching `source_revision`, actual `run_id`, `target`, timezone-aware ISO-8601
`started_at` and `finished_at`, actual `command` argv and `exit_code`, nonempty
`test_sources` and run-level `evidence` arrays of `{path, sha256}`, and `cases`.
Each case has a planned `id` and a status:
`passed`, `failed`, `skipped`, `blocked`, `not_run`, or `flaky`.
A passed case additionally requires `test_ref` matching a hashed test source,
`asserted_requirements` exactly matching the plan, and nonempty hashed
`evidence`. Keep retries in the raw report and normalize fail-then-pass as
`flaky`. Unexpected or duplicate IDs are invalid; missing IDs become `not_run`.

File hashes bind current project-contained source, tests, and evidence bytes.
Absolute paths, parent traversal, and symlink escapes are rejected. Manifest,
source revision, source bytes, test bytes, or evidence drift invalidates old
results. No unexecuted case may disappear from the denominator. The report
separates requirement coverage, statuses, t-way interactions, missing mandatory
combinations, and the original runner exit code.

## Limits and integration readiness

`complete_against_frozen_scope` is a bounded **model/evidence consistency** claim.
The helper cannot prove that discovery found every feature, that a supplied
report is truthful, that the intended binary was executed, or that a UI is
visually acceptable. The workflow requires independent inventory/report review
and explicit qualifications; missing visual review remains pending human review.
No software test suite here claims mathematical completeness or release safety.

The branch's merge gates and outstanding catalog/installation work are recorded
in [E2E readiness](../plans/sp-e2e-readiness.md). Until those gates are closed,
this is a draft implementation, not an installed/released workflow guarantee.
