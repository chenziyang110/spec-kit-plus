{{spec-kit-include: ../common/user-input.md}}

## Objective

Reconstruct or refresh the query-backed project cognition runtime from a completed evidence baseline.

## Context

- Primary inputs: `.specify/project-cognition/status.json`, `.specify/project-cognition/evidence/`, `.specify/project-cognition/provisional/nodes.json`, `.specify/project-cognition/provisional/edges.json`, `.specify/project-cognition/provisional/observations.json`, and live repository evidence.
- This command owns the query-backed cognition runtime outputs: `.specify/project-cognition/status.json` and `.specify/project-cognition/project-cognition.db`.
- After the SQLite DB is published, run `{{specify-subcmd:project-cognition publish-runtime-metadata --format json}}` before `validate-build` so `baseline_state`, `graph_ready`, `graph_store_path`, and `active_generation_id` are written from the DB into the metadata table and status entrypoint.
- If the evidence baseline is incomplete or the accepted evidence cannot support graph reconstruction, produce a scan gap report and return to `sp-map-scan`.
- Record accepted and rejected reconstruction evidence as DB/runtime update records and queryable task-local bundle readiness metadata. Treat any raw graph or slice files as compatibility/export artifacts, not runtime truth.
- Apply project cognition ignore rules from root `.cognitionignore` and `.specify/project-cognition/.cognitionignore`; rejected paths remain outside graph evidence and DB route indexes even when scan artifacts mention them.
