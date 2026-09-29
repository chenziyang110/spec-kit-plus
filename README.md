### Workflow catalog

| Layer | Canonical workflows |
| --- | --- |
| Core workflow skills | `constitution`, `specify`, `plan`, `tasks`, `implement`, `review`, `accept` |
| Support skills | `auto`, `ask`, `discussion`, `deep-research`, `test-design`, `design`, `fast`, `quick`, `checklist`, `analyze`, `debug`, `explain`, `implement-teams`, `prd-scan`, `prd-build`, `map-scan`, `map-build`, `map-update`, `taskstoissues` |
| Codex-only runtime | `sp-teams` for durable managed-team state and `team` for runtime operations inside the generated agent catalog |

The generated `ask` workflow is read-only, evidence-backed project Q&A. `prd-scan -> prd-build` reconstructs current product documentation from an existing repository and is a peer workflow, not an automatic handoff to `plan`.

## Workflow profiles

| | Classic | Advanced |
| --- | --- | --- |
| Best fit | Broad compatibility and explicit guidance | Advanced models that can operate from compact, independently owned skills |
| Availability | Every integration | Skills-based integrations only |
| Generated surface | Agent-native `sp-*` skills or `/sp.*` commands | Independent `spx-*` skills plus the original Classic map companions |
| Prompt policy | Full tutorials, recovery guidance, and compatibility detail | Removes repetition and stable boilerplate while preserving state, recovery, side-effect, and final-claim gates |
| Default | Non-interactive default | Explicit opt-in with `--workflow-profile advanced` |
