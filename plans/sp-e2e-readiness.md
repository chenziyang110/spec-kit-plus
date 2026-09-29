# SP E2E implementation readiness

## Product direction

E2E is scenario-first test analysis/design across desktop/mobile clients, web,
CLI and services. A visual model with actual inspection/interaction tools is a
first-class execution route; browser runners and executable test files are not
entry requirements. The model derives semantics; deterministic helpers account
for declared coverage and evidence. Test Design remains a read-only optional
producer, while Review/Accept retain their existing authority.

## Implemented in this branch

- Independent Classic/Advanced workflows for operation inventories, assumptions,
  error guessing, input classes/boundaries, state transitions, event order,
  external mutations, visual interaction, recovery and cross-feature effects.
- A shared standard-library scenario helper with a 14-dimension question catalog,
  book/trace JSON Schemas, event/checkpoint obligation expansion, design gap
  checks, source/evidence hashing and visual/mixed trace accounting.
- Exact scenario cards with ordered actions, perturbation steps, assertions,
  observation channels, safe setup/cleanup and explicit execution routes.
  Screenshots cannot fill independent durable-effect oracles. Failed/skipped/
  blocked/not-run/flaky cases and cleanup failures cannot close the run.
- A rename derivation example with 26 candidate families and a concrete visual
  scenario card; explicit platform-limit, object-identity and oracle-gap rules.
- The existing constrained t-way planner/audit and native pytest/Playwright
  wrappers remain an optional lane. No changes to their implementation were
  made in the scenario-first continuation.

## Verification recorded by revision

The initial `0dbc55d` implementation recorded 57 coverage-helper tests and 4
workflow-source tests passing. The native-runner continuation ending at
`2a8ad1f` recorded 48 runner tests passing in two local batches, including a real
disposable CLI/SQLite sample. These are historical local results, not later
full-repository or installed-profile evidence. Playwright checks were parser
fixtures, not browser runs.

The scenario-first continuation locally ran:

```text
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/test_e2e_scenarios.py tests/test_e2e_workflow_contract.py tests/test_e2e_scenario_workflow_contract.py -q
74 passed
```

That is 65 new helper/schema/CLI tests, 5 new cross-profile source checks and the
4 existing E2E source tests, in an isolated Linux/Python 3.13.5/pytest 9.0.2
workspace. The original source test file was preserved byte-for-byte. Book and
trace examples are explicitly labeled synthetic fixtures. No actual desktop,
mobile, visual-model or browser E2E execution is claimed. Tests establish the
helper's declared accounting, not truthful perception or complete discovery.

The environment could not clone the private source through container Git
(network DNS resolution failed). Focused files were read through the authorized
GitHub connector; the whole repository/dependency environment was not present.
No full-repository Python/Go or installation suite was run. Do not add isolated
and historical counts together and relabel them product readiness.

## Still required before merge

1. Register e2e in shared cognition closeout policy and its Go owner; audit
   Learning, workflow-name validation, reserved names, orchestration and argument
   hints. Preserve the existing Work Board route, not an unsupported Activity.
2. Add spx-e2e and its scenario-design reference to the Advanced surface map and
   expected SPX catalog; synchronize profile counts, README, PROJECT-HANDBOOK,
   profile guidance and init Start Here. Source directories alone are not enough.
3. Verify Classic/Advanced installation, helper copying, generated commands,
   sidecars, manifests, hooks, dual-profile coexistence and wheel contents.
   Existing scripts/shared force-inclusion alone is not installed availability.
4. Execute a real client sample through available visual inspection/interaction
   and independent state tools. Verify deletion/rename/replacement timing and
   invalid/boundary inputs against that sample's actual contract. This is a
   distinct gate from an actual browser run of the optional Playwright adapter.
5. Run affected/full Python and Go suites, Python 3.11/3.12, native Windows/macOS,
   final diff checks and real cloud CI. Distributed pytest/shard merging remain
   explicitly unsupported, never silently treated as complete coverage.

Keep the PR draft until these gates are closed. Preserve existing tests; do not
weaken catalog checks, fabricate perception evidence, change repository
visibility, merge or publish a release as part of this maintenance request.
