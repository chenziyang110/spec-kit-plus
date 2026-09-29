---
name: spx-e2e
description: Advanced user-invoked end-to-end execution with a frozen requirement universe, constrained t-way combinations, real runner evidence, and explicit gap accounting.
---

# E2E execution

Run only when explicitly invoked. Read `references/project-cognition.md` and
`references/project-learning.md` for navigation and relevant lessons; live
repository evidence and intended contracts remain authoritative. Apply
`references/execution-bootstrap.md` using the other-modifying-workflows Work
Board route, not a new `execution announce` workflow enum. Use supported runtime
help/discovery; never impersonate another workflow or invent a runtime E2E API.
Read `references/blocker-resolution.md` at a blocked boundary.

Own executable E2E test assets, fixtures, adapters, scoped harness configuration,
and ordinary test results. Do not modify production behavior, migrations,
registered design truth, Test Design packages, or feature lifecycle state.
Resolve scope explicitly; an unqualified full E2E request means the current
product, not merely the changed files. Preserve unrelated work and declare
exact write paths/resources before mutation. Use isolated safe environments,
accounts, seeds, reset/cleanup, readiness checks, and per-worker namespaces.
Production transactions, credentials, external writes, dependency upgrades,
license acceptance, and deployment remain separately authorized boundaries.

## Discover and freeze

Reconcile intended requirements/acceptance/design sources with implemented
routes, APIs, commands, roles, configuration, jobs, integrations, and durable
state. Existing tests do not define the denominator. A current Test Design
publication is optional, read-only input through its supported verification
route; preserve its IDs and gaps without inventing an E2E projection consumer.
Contradictions and unread/unknown surfaces remain explicit discovery gaps.

Build stable requirements and complete real-entrypoint journeys with independent
business-outcome and persistence/readback assertions. Include cross-feature
handoffs, authorization/tenant isolation, invalid/boundary/empty data, timeout,
cancel, retry, duplicates, conflict/concurrency, and interruption/recovery.
Negative actions that must be rejected are tests, not infeasible combinations.
Separate ordered/stateful paths into distinct journeys; pairwise parameters
cannot establish event-order coverage. Preserve design/source-continuity IDs
for UI-bearing paths and read `references/ui-quality-gate.md` when applicable.

Persist a versioned manifest in the existing E2E test tree. Hash all selected
source/contract/config/fixture inputs; record revision and dirty/build identity.
Every requirement must map to an executable journey. Define concrete applicable
factor values, justified infeasibility constraints, pairwise strength by default,
mandatory known-risk higher-order assignments, and higher t-way or exhaustive
coverage for critical bounded matrices. Explain omitted dimensions and explicit
scope exclusions. Never shrink scope to hide a failing or unavailable test.

## Compile, implement, run

The shared dependency-free helper is installed at
`.specify/scripts/shared/e2e_coverage.py`; use the verified Python 3.11+ interpreter:

```text
python .specify/scripts/shared/e2e_coverage.py plan tests/e2e/coverage-manifest.json --root . --max-cases 1000
```

Freeze its stdout as `plan.json` for a new immutable run. A successful plan is
`planned_only`. Preserve generated `E2E-*` IDs and the full denominator. Budget
failure requires explicit scope/budget revision or a split retaining cross-scope
journeys; no silent strength reduction or sampling. Implement missing real
parameterized tests using the project's actual runner and fixture conventions,
plus a deterministic adapter from original runner reports. The adapter must
retain actual assertions, collected IDs, attempts, exit code, and evidence;
never author passing results from a plan.

Compare runner collection to the generated IDs, rejecting missing, duplicate,
and unknown cases. Execute the actual product from official entrypoints, not a
mock-only/unit substitute. Bind external sandbox/mocked boundaries explicitly
and preserve live integration gaps. Preserve raw reports, traces/screenshots
when relevant, timestamps, diagnostics, test/build hashes, and cleanup outcome.
Shards may join only when disjoint and bound to the same manifest, build,
environment, and run; missing shards remain not run. Smoke/filtered execution
cannot close a full manifest. Do not let shell pipelines hide runner failure.

Keep retries visible: fail-then-pass is flaky. Skipped, disabled, quarantined,
unsupported, blocked, and never-run tests are not passes. Repair bounded harness
issues and rerun affected tests plus shared-fixture regressions; keep product
defects failed with reproductions and return them to their owner. Relevant
source, test, fixture, configuration, or contract changes invalidate old evidence.
Do not silently invoke a different workflow to repair production code.

## Verify and qualify

```text
python .specify/scripts/shared/e2e_coverage.py audit tests/e2e/coverage-manifest.json --root . --results test-results/e2e/<run-id>/results.json --max-cases 1000
```

Audit rebuilds feasible interactions and expected cases, verifies source/test/
evidence hashes, and exposes missing requirements, cases, tuples, and mandatory
combinations. Exit 0 means complete against the frozen model, 1 incomplete,
2 invalid/stale. It is not proof that discovery was exhaustive or that supplied
runner evidence is truthful. Independently audit inventories, exclusions,
constraints, negative/ordered journeys, assertions, collection, and provenance.
If no independent reviewer is available, perform a documented second pass and
retain the unverified-independence qualification.

Return separate requirement, case-execution, t-way interaction, and mandatory
combination coverage; all failed/skipped/blocked/flaky/not-run IDs; source
freshness, discovery gaps, exclusions, and evidence refs. A bounded final claim
requires all in-scope cases passed, zero discovery gaps, a successful original
runner, and fresh evidence. Missing visual comparison is pending-human-review.
No absolute completeness, release-safety, or acceptance claim is permitted.
Formal delivery remains tasks -> implement -> review -> accept; this lane is
additional evidence, not a bypass. Resume by rechecking hashes and regenerating
the denominator; retain old run artifacts. Close Work only with fresh valid
verification, never a fabricated pass.

At a real blocked exit preserve stage, category, owner, exact cause, sanitized
evidence, attempted recovery, affected IDs, next action, observable unblock
criteria, and exact resume point. Repair agent-owned harness issues in-session;
never request secrets or transfer lifecycle repair to the user.

## Shared JSON contract

Manifest: `schema_version: 1`, `scope`, `source_revision`, nonempty
`sources: [{path, sha256}]`, `exclusions: [{scope, reason}]`,
`requirements: [{id, source, assertion}]`, and
`journeys: [{id, requirements, steps, factors, strength, exclude, mandatory}]`.
Factors map names to distinct nonempty string arrays. Strength is an integer or
`"exhaustive"`; exclusions are `{when: {factor: value}, reason}`; mandatory rows
are partial assignments. All hashed file paths must stay project-relative.

Results: `schema_version: 1`, exact `manifest_sha256`, `source_revision`, actual
`run_id`, `target`, `started_at`, `finished_at`, `command` argv, `exit_code`,
`test_sources`, run-level `evidence` (both `{path, sha256}` arrays), and
`cases: [{id, status, test_ref, asserted_requirements, evidence}]`. Status is
`passed|failed|skipped|blocked|not_run|flaky`. A passed case binds a hashed test
source, all its exact requirement assertions, and nonempty hashed evidence.
These files are ordinary test assets/results, not runtime workflow state.

## Supplied native runner adapters

For serial pytest and Playwright Test, reuse
`.specify/scripts/shared/e2e_runner.py` instead of authoring normalized passing
results or rebuilding an adapter. Freeze a bindings JSON with `schema_version`,
`manifest_sha256`, hashed `test_sources`, and a `cases` array containing every
planned `id`, `test_ref`, `selector`, and `asserted_requirements`. The selector
contains exactly one complete generated case ID. pytest uses its full nodeid;
Playwright uses its exact test title plus the exact `project` name. Browser and
project combinations require distinct planned IDs. Independently inspect the
bound assertions; bindings are not proof of assertion quality.

```text
python .specify/scripts/shared/e2e_runner.py tests/e2e/coverage-manifest.json --bindings tests/e2e/bindings.json --root . --runner pytest --target local-test-build --output-dir test-results/e2e/run-001 -- tests/e2e -q
python .specify/scripts/shared/e2e_runner.py tests/e2e/coverage-manifest.json --bindings tests/e2e/bindings.json --root . --runner playwright --target local-test-build --output-dir test-results/e2e/run-002 -- node node_modules/@playwright/test/cli.js test tests/e2e
```

Use only an already installed, authorized runner and a new output directory.
The wrapper preserves native reports, all pytest phases/attempts, actual process
exit status, and fresh source/test bindings, then runs the coverage audit.
Untracked collected tests, stale evidence, duplicates, and missing reports fail
closed. It does not support distributed pytest or shard merging; a partial
shard cannot complete a full manifest. Other harnesses require an explicitly
validated adapter. Do not silently install missing helpers or runners, fall back
to invented results, or treat these adapters as product acceptance.
