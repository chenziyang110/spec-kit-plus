### Workflow catalog

| Layer | Canonical workflows |
| --- | --- |
| Core workflow skills | `constitution`, `specify`, `plan`, `tasks`, `implement`, `review`, `accept` |
| Support skills | `auto`, `ask`, `discussion`, `deep-research`, `test-design`, `e2e`, `design`, `fast`, `quick`, `checklist`, `analyze`, `debug`, `explain`, `implement-teams`, `prd-scan`, `prd-build`, `map-scan`, `map-build`, `map-update`, `taskstoissues` |
| Codex-only runtime | `sp-teams` for durable managed-team state and `team` for runtime operations inside the generated agent catalog |

The generated `ask` workflow is read-only, evidence-backed project Q&A. `prd-scan -> prd-build` reconstructs current product documentation from an existing repository and is a peer workflow, not an automatic handoff to `plan`.

## Scenario-first E2E

Use `sp-e2e` (Classic) or `spx-e2e` (Advanced) to derive abnormal, boundary,
state-change and event-order tests for desktop/mobile clients, web, CLI and
services, then execute through available visual-model tools or existing runners.
For example, external deletion after opening a rename dialog is a different
scenario from deletion immediately before confirmation. Existing tests and a
green process exit do not define complete coverage. Planning-only output, actual
execution, independent effect checks and visual/human acceptance stay separate.

See [E2E usage](docs/sp-e2e.md), [scenario design](docs/sp-e2e-scenarios.md),
[desktop validation sample](docs/sp-e2e-desktop-sample.md) and
[readiness limits](plans/sp-e2e-readiness.md). No browser harness is required for
a usable client visual route. Formal delivery remains
`tasks -> implement -> review -> accept`.

## Workflow profiles

| | Classic | Advanced |
| --- | --- | --- |
| Best fit | Broad compatibility and explicit guidance | Advanced models that can operate from compact, independently owned skills |
| Availability | Every integration | Skills-based integrations only |
| Generated surface | Agent-native `sp-*` skills or `/sp.*` commands | Independent `spx-*` skills plus the original Classic map companions |
| Prompt policy | Full tutorials, recovery guidance, and compatibility detail | Removes repetition and stable boilerplate while preserving state, recovery, side-effect, and final-claim gates |
| Default | Non-interactive default | Explicit opt-in with `--workflow-profile advanced` |
