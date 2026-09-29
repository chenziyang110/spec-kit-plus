---
description: Execute real end-to-end journeys against a frozen feature inventory, verify constrained combinations, and expose every missing, skipped, failed, or stale test instead of claiming sampled happy paths are complete.
workflow_contract:
  when_to_use: Explicitly requested project-wide, feature-scoped, or regression E2E execution after runnable implementation exists.
  primary_objective: Discover the complete declared test boundary independently of existing tests, implement missing executable E2E assets, run the real product, and audit requirement, interaction, and execution coverage separately.
  primary_outputs: Versioned E2E manifest and executable test assets in the existing test tree, plus immutable per-run runner evidence, normalized results, coverage audit, and explicit gaps under the project's test-results directory.
  default_handoff: Return the evidence and unresolved gaps to the caller; formal delivery still requires /sp.review followed by /sp.accept.
---

{{spec-kit-include: ../command-partials/common/user-input.md}}

# End-to-End Execution with Coverage Accounting

This is the user-invoked `sp-e2e` execution lane, not Test Design, a unit-test
checklist, or human acceptance. Do the work: discover, model, implement missing
tests, execute, and reconcile evidence. A plan or green smoke test is not the
requested result. Support browser, API, CLI, desktop, or service journeys using
the project's actual supported harness; do not assume Playwright is installed.

{{spec-kit-include: ../command-partials/common/execution-bootstrap.md}}

## Ownership and Safe Entry

1. Resolve the explicitly selected project/feature and inspect the working tree.
   Default an unqualified request for full E2E to the entire current product,
   not just the latest diff. A feature or changed-only request must name the
   narrower boundary and retain affected cross-feature regression journeys.
   Never infer a feature from a branch name. Preserve unrelated changes.
2. Read relevant Learning and use project cognition as navigation, then verify
   against live code, contracts, configuration, and official entrypoints. Use
   supported runtime discovery/help; do not invent `specify e2e`,
   `specify-runtime e2e`, a Test Design `e2e` projection consumer, or an
   `execution announce --workflow e2e` enum. If a runtime rejects an unsupported
   workflow token, report a capability gap rather than impersonating another
   workflow. Apply the shared bootstrap's **other modifying workflows** Work
   Board route before test-asset writes; E2E does not own a new Activity type.
3. Own only the scoped E2E tests, deterministic fixtures, adapters, manifest,
   and necessary test-harness configuration. Product behavior, migrations,
   design approval, Test Design publications, and feature workflow state remain
   outside this write boundary. Report product defects with reproducible cases
   to the original owner; do not weaken assertions or patch production code
   merely to obtain green tests. Do not invoke another workflow implicitly.
4. Establish an isolated local/test environment, safe test accounts/roles,
   deterministic seeds and clocks where needed, per-worker namespaces, reset
   and cleanup, and service readiness checks. Record actual URLs/entrypoints,
   build identity, dependency modes, and unavailable resources. Never operate
   on production data, send real payments/messages, install/upgrade dependencies,
   accept licenses, or use credentials beyond authorization. Genuine external
   boundaries stay blocked; never substitute a mock and label it full-stack E2E.

## 1. Discover the Denominator Before Choosing Tests

Reconcile two independent inventories: intended behavior from specifications,
acceptance criteria, registered design contracts, and a current Test Design
publication when present; implemented behavior from routes, menus, APIs/CLI
commands, permissions, jobs, integrations, configuration, and persisted state.
Existing tests are evidence about coverage, never the universe of features.
Read a Test Design publication only through its supported read/verification
routes and preserve its source IDs and gaps; do not create a new producer
projection type or mutate that package. It is optional, not an entry gate.

Record stable requirement IDs and source refs for every user-visible capability,
business rule, failure/recovery outcome, and applicable regression obligation.
Disagreements between intended and implemented behavior are defects or explicit
scope decisions, not reasons to remove requirements. Track unread paths and
unknown surfaces as discovery gaps. Audit all discovered entrypoints against
this inventory before declaring the boundary frozen.

Build complete journeys from real entrypoint through externally observable
outcome and durable side effect: setup -> user actions -> authorization ->
service/storage boundary -> reload or independent readback -> cleanup. Include
cross-feature handoffs. Represent success, denial, invalid/boundary/empty data,
timeout/cancel/retry, duplicate submission, state transitions, conflict,
concurrent actors, and interrupted/resumed execution as separate journeys when
they need different oracles. A route loading or HTTP 200 is not an adequate
business-outcome assertion. UI journeys preserve design/source-continuity IDs;
automation never replaces visual/interaction judgment.

## 2. Freeze and Compile the Combination Model

Keep the manifest in the project's existing test tree, for example
`tests/e2e/coverage-manifest.json`. Use the JSON contract documented by the
installed helper and this command's output contract below. Hash every selected
source/contract/config/fixture defining the tested behavior; record the Git
revision plus dirty-tree/build identity in the run notes. Maintain explicit
excluded scopes with reasons and owners; exclusions remain visible in reports.

For each journey define factors and concrete values: roles/tenants, lifecycle
states, data classes, flags/configurations, browser/device/viewport, locale,
network/dependency outcomes, and relevant concurrent actors. Select only
applicable factors but explain omitted dimensions. Use `strength: 2` for ordinary
pairwise coverage, explicit mandatory three-or-more-factor combinations for
known risks, and `strength: 3` or `"exhaustive"` for critical bounded matrices.
Pairwise is not exhaustive and cannot cover ordered events; encode event order
as distinct journeys with explicit steps and postconditions.

`exclude` constraints may remove only genuinely infeasible configurations, with
an evidence-backed reason. An invalid input or forbidden user action that the
product must reject is a **required negative test**, not an infeasible scenario.
Never exclude failures, lack of fixtures, time budgets, or unsupported test
infrastructure. Keep these as gaps/blocked cases. The helper rejects dead factor
values, impossible mandatory combinations, and unbounded matrices.

Run the deterministic planner from the project root, using the installed Python
3.11+ interpreter (`python`, `python3`, or the verified Windows launcher):

```text
python .specify/scripts/shared/e2e_coverage.py plan tests/e2e/coverage-manifest.json --root . --max-cases 1000
```

Save stdout as a new run's `plan.json`; check the exit code first. Do not change
case IDs, omit generated rows, lower interaction strength, or silently sample
to fit a budget. Split a large model into auditable scopes only when cross-scope
journeys are preserved, or explicitly agree the revised boundary. Every
requirement must map to at least one executable journey; every generated case
must become a parameterized runnable test with its stable `E2E-*` ID.

## 3. Implement and Execute the Real Suite

Reuse the actual runner, selectors, fixture conventions, isolation, and CI
entrypoint. Implement missing cases and a deterministic runner-report adapter
inside the declared test-asset scope. The adapter maps collected test IDs and
actual attempts to generated case IDs, assertion requirements, test sources,
and original evidence; it never synthesizes passing outcomes. Each selected
case must have observable assertions for every referenced requirement.

Compare runner **collection** with `plan.json` before execution. Fail on missing,
unknown, or duplicate case IDs. Retain the entire denominator across shards;
merge only disjoint shards from the exact same manifest, source/build,
environment, and run identity. Missing shards remain `not_run`. A filtered smoke
or changed-only run must not close a full manifest.

Start from official product entrypoints and execute the commands, not simulated
interactions or snippets disconnected from the application. Assert public
outcomes and independent persistence/readback where relevant. Mocks needed for
external sandbox boundaries must be explicit per journey, with the corresponding
live integration gap retained. Preserve process exit codes and original runner
reports, timestamps, test/build hashes, diagnostics, screenshots/traces when
available, and cleanup outcomes. Do not let shell pipelines hide runner failure.

Retain every attempt: fail-then-pass is `flaky`, not clean `passed`; disabled,
quarantined, unsupported, blocked, skipped, and never-run tests are not passes.
Repair test-harness issues within scope and rerun affected cases plus shared
fixture regressions. Product defects remain failed with a reproduction and
owner. After any relevant source/test/config change, refresh the manifest
binding and rerun; previous evidence must not silently carry over.

## 4. Audit Coverage and Close Truthfully

Normalize only actual runner evidence into `results.json` and run:

```text
python .specify/scripts/shared/e2e_coverage.py audit tests/e2e/coverage-manifest.json --root . --results test-results/e2e/<run-id>/results.json --max-cases 1000
```

The helper independently rebuilds the case denominator and feasible interactions,
checks source/test/evidence hashes, and reports missing cases and tuples. Exit 0
means consistency and completion against **this frozen model**; exit 1 means
incomplete execution; exit 2 means invalid/stale input. A planner exit 0 means
`planned_only`, never tests passed. Do not overwrite previous run evidence or
hand-edit the audit to change a claim.

Have an independent read-only reviewer reconcile the original entrypoint and
requirement inventories, constraints, negative/ordered journeys, assertions,
runner collection, and report provenance. When an independent reviewer is
unavailable, perform a second explicit audit pass and report that independence
is unverified; do not claim independently audited completeness. The helper
checks a supplied model and evidence bindings, not whether the model omitted a
feature or whether a report is truthful.

Report requirement coverage, planned/executed/passed cases, feasible t-way
interaction coverage, mandatory risky combinations, skips/blocked/flaky cases,
source freshness, discovery gaps, exclusions, and evidence refs separately.
A bounded completion claim requires zero unresolved discovery gaps, all
in-scope cases passed, all mandatory combinations exercised, fresh evidence,
and the original runner succeeded. UI visual comparison that could not be
performed remains `pending-human-review`, even with automation green.
Never claim absolute completeness, release safety, or accepted product status.
Formal delivery remains `tasks -> implement -> review -> accept`; E2E evidence
is an additional input, not permission to bypass Review or human acceptance.

At a blocked exit name stage, category, owner, exact cause, sanitized evidence,
recovery attempted, affected IDs, next action, observable unblock criteria, and
exact resume point. Agent-capable test-harness recovery stays agent-owned;
never ask for secrets or make the user reconstruct state. On resume rerun the
planner/hash checks before using old artifacts. Close Work only after the
required validation; do not fabricate a terminal pass to release ownership.

## Machine Input Contract

The manifest has `schema_version: 1`, `scope`, `source_revision`, nonempty
`sources: [{path, sha256}]`, `exclusions: [{scope, reason}]`,
`requirements: [{id, source, assertion}]`, and
`journeys: [{id, requirements, steps, factors, strength, exclude, mandatory}]`.
`factors` maps names to nonempty arrays of distinct strings; `exclude` entries
are `{when: {factor: value}, reason}`; `mandatory` entries are partial factor
assignments. All paths in hashed file records are project-relative.

Results have `schema_version: 1`, the planner's `manifest_sha256`, matching
`source_revision`, actual `run_id`, `target`, `started_at`, `finished_at`,
`command` argv, `exit_code`, `test_sources` and run-level `evidence` arrays of
`{path, sha256}`, and `cases: [{id, status, test_ref, asserted_requirements,
evidence}]`. Status is `passed|failed|skipped|blocked|not_run|flaky`. A passed case
must bind its executable `test_ref` to a hashed test source, assert exactly its
planned requirements, and cite nonempty hashed original evidence. Missing cases
are `not_run`. These are ordinary test assets/results, **not** runtime-owned
workflow state, publications, acceptance receipts, or a new runtime command.
