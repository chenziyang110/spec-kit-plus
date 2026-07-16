{{spec-kit-include: ../common/user-input.md}}

## Objective

Reconstruct or refresh the query-backed project cognition runtime from a completed evidence baseline.

## Context

- Primary inputs: `.specify/project-cognition/status.json`, `.specify/project-cognition/evidence/`, `.specify/project-cognition/provisional/nodes.json`, `.specify/project-cognition/provisional/edges.json`, `.specify/project-cognition/provisional/observations.json`, and live repository evidence.
- This command owns the query-backed cognition runtime outputs: `.specify/project-cognition/status.json` and `.specify/project-cognition/project-cognition.db`.
- Run `{{specify-subcmd:project-cognition build-from-scan --format json}}` after scan and package validation. It adapts the accepted canonical scan package into a versioned proposal and runs the deterministic cognition proposal compiler before any graph-store mutation; only a publishable result may continue to DB import, metadata, status publication, and DB/status agreement.
- Treat `compilation.publication_allowed=false` as a hard pre-publication block and stop without creating, archiving, replacing, or publishing the graph store.
- Successful compilation preserves advisory graph material as route candidates rather than repository facts; prove behavioral claims from live repository evidence.
- [AGENT] Treat sparse path-index gates as build preflight; do not publish query-ready status when `validate-build` would fail `path_index_to_included_ratio`, critical path, or important path checks.
- Do not construct `.specify/project-cognition/project-cognition.db` with manual SQL as the normal workflow path.
- If the evidence baseline is incomplete or the accepted evidence cannot support graph reconstruction, produce a scan gap report and return to `sp-map-scan`.
- If scan packet intake exposes contract-invalid, systemic packet-family failures, or `paths_read` values that are not concrete path arrays, preserve the scan gap report and route back to `sp-map-scan`; this is not only a local patch in build.
- Record accepted and rejected reconstruction evidence as DB/runtime update records and queryable task-local bundle readiness metadata. Treat any raw graph or slice files as compatibility/export artifacts, not runtime truth.
- Apply project cognition ignore rules from root `.cognitionignore` and `.specify/project-cognition/.cognitionignore`; rejected paths remain outside graph evidence and DB route indexes even when scan artifacts mention them.
- Validate `repository-universe.json` as the canonical scan boundary before graph reconstruction; excluded paths are boundary facts, not graph evidence.
- If native subagent dispatch is unavailable or a substantive build lane cannot complete, persist `subagent_blocked` in machine-readable state and block baseline activation until recovery. `coverage-ledger.json.open_gaps[]` may use `low_risk_open_gap` only with owner, reason, evidence expectation, and revisit condition.
