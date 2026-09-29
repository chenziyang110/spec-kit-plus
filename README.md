| Core workflow skills | `constitution`, `specify`, `plan`, `tasks`, `implement`, `review`, `accept` |
| Support skills | `auto`, `ask`, `discussion`, `deep-research`, `test-design`, `e2e`, `design`, `fast`, `quick`, `checklist`, `analyze`, `debug`, `explain`, `implement-teams`, `prd-scan`, `prd-build`, `map-scan`, `map-build`, `map-update`, `taskstoissues` |
| Codex-only runtime | `sp-teams` for durable managed-team state and `team` for runtime operations inside the generated agent catalog |

The generated `ask` workflow is read-only, evidence-backed project Q&A. `prd-scan -> prd-build` reconstructs current product documentation from an existing repository and is a peer workflow, not an automatic handoff to `plan`.

## Scenario-first E2E testing

Use `sp-e2e` / `spx-e2e` to derive tests from operations and their assumptions,
not merely replay existing happy-path tests. Desktop/mobile clients, web, CLI
and services share the same scenario-analysis contract. Challenge input classes,
actual limits, object identity, external changes, event order, permissions,
concurrent actors, interruption/recovery and downstream effects.

For example, deleting a file while its rename dialog is open and deleting it
immediately before confirmation are separate obligations. A log or success
message cannot replace independent verification of the actual file state.
Visual-model inspection/interaction is a first-class execution route; neither
Playwright nor an executable test file is required to plan or visually execute
client scenarios. Missing capabilities remain visible gaps, never exclusions.

[Workflow and invocation](docs/sp-e2e.md), [scenario design and rename examples](docs/sp-e2e-scenarios.md),
and [optional native runners](docs/sp-e2e-runner.md) explain the distinct design,
execution and evidence claims. Test Design remains an optional read-only input;
formal delivery still requires `tasks -> implement -> review -> accept`.
See [readiness](plans/sp-e2e-readiness.md) for unverified release boundaries.

## Workflow profiles

| | Classic | Advanced |
| --- | --- | --- |
