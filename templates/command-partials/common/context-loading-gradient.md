## Project Cognition Gate

This command must treat the project cognition runtime as the mandatory pre-source knowledge base.

### Hard Rule

Do not inspect implementation source, run reproduction or tests, compile a
plan, prepare a fix, or emit technical recommendations until the cognition gate has
passed.

### Required Project Cognition Artifacts

- Read `.specify/project-cognition/status.json`.
- Read the required graph slice or graph context artifacts for the active workflow.
- Use `.specify/project-cognition/graph/nodes.json`, `.specify/project-cognition/graph/edges.json`, `.specify/project-cognition/graph/claims.json`, and `.specify/project-cognition/graph/conflicts.json` when the workflow contract requires deeper graph-native context.

### Fixed Artifact Consumption

Every workflow must read the required project cognition status and graph slice artifacts explicitly required by its command contract.
Do not replace slice consumption with broad freeform repository rereads when the graph runtime already covers the touched area.

### Command Tier Depth

Tier determines how deeply the workflow must continue through graph slices and graph artifacts
after the minimum gate, not whether it may skip cognition-runtime consumption.

- `trivial`: minimum required artifact set only
- `light`: minimum artifact set plus relevant routing or playbook artifacts
- `heavy`: minimum artifact set plus all relevant collaboration, propagation, and verification artifacts

### Freshness

Treat graph-runtime freshness as a gate:

- `missing` -> block and refresh through `sp-map-scan -> sp-map-build`
- `stale` -> block and refresh through `sp-map-update`
- `support_drift` -> stop and tell the user to resolve support-surface drift; do not reflexively route to `sp-map-update`
- `partial_refresh` -> tell the user the refresh was recorded but readiness did not pass; follow `recommended_next_action`
- `possibly_stale` -> inspect the affected graph scope; if the touched area is not safely covered, route through `sp-map-update`

Preserve the distinction between the machine freshness field and public state
guidance: consume `freshness` as the factual state and use
`recommended_next_action` for the operator-facing next step.

### Primary Read Restriction

Do not treat handbook-first or layered project-map files as the primary runtime read surfaces. If graph-native
coverage is insufficient, refresh the cognition runtime through `sp-map-update` or rebuild through `sp-map-scan -> sp-map-build`
instead of forcing a second handbook traversal phase.
