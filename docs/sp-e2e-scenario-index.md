# Indexed scenario accounting

The shared `scripts/shared/e2e_scenarios.py` helper builds operation-local
allowed timing pairs once during structural validation, then indexes scenario
coverage by operation and by `(operation, event, checkpoint)` during checking.
This replaces repeated scans of the entire scenario/timing inventory. Classic
`sp-e2e` and Advanced `spx-e2e` consume the same helper; no profile or schema fork
is introduced.

The index is local to each call. Operation IDs remain part of timing keys so
identically named events in different operations cannot satisfy one another.
Reports still follow the original inventory and sorted obligation order, including
sorted scenario IDs, missing requirements, discovery gaps and condition gaps.
Source checks, v1/v2 interpretation, boundary units, explicit event/checkpoint
obligations, exact oracle bindings, budgets and all nonpassing states are unchanged.
An index does not discover missing product requirements or authorize acceptance.

## Regression and comparison

`tests/test_e2e_scenario_index.py` compares full reports against the original
rescan joins for 64 fixed seeds in each schema version. It also checks operation
isolation, unknown timing, empty scope, budget refusal, unchanged input, native
scenario audit statuses and benchmark mismatch rejection. Traversal-count checks
bound repeated perturbation scans without an unstable wall-clock CI threshold.
The original scenario, condition and seven-stage source-contract suites remain
separate checks; source-contract tests are not Go runtime execution tests.

From a complete checkout, reproduce the focused suite:

```sh
uv run pytest tests/test_e2e_scenarios.py tests/test_e2e_conditions.py tests/test_e2e_scenario_index.py tests/test_e2e_workflow_contract.py -q
```

The benchmark imports two explicit trusted Python modules, validates every full
output and unchanged input, alternates their order and reports all raw timings,
medians, environment and source hashes. Do not supply untrusted modules.

```sh
git show 7c278cea9d53af7ef0fe06f0f58667209cb47458:scripts/shared/e2e_scenarios.py > /tmp/e2e_scenarios_before.py
python tools/workflow-quality/benchmark_e2e_scenarios.py --baseline /tmp/e2e_scenarios_before.py --repeats 5
```

These are synthetic design-accounting workloads, not application executions.
The audit workloads deliberately supply no execution results: every scenario
remains `not_run`, and faster computation must not change that result. No timing
ratio establishes browser, native device or complete workflow speedup. Full
repository dependencies, Go state/handoff behavior, both installed profiles,
wheel/init/upgrade/repair, real product routes and independent acceptance remain
separate required gates.
