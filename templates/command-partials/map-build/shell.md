{{spec-kit-include: ../common/user-input.md}}

## Objective

Reconstruct or refresh the query-backed project cognition runtime from a completed evidence baseline.

## Context

- Primary inputs: `.specify/project-cognition/status.json`, `.specify/project-cognition/evidence/`, `.specify/project-cognition/provisional/nodes.json`, `.specify/project-cognition/provisional/edges.json`, `.specify/project-cognition/provisional/observations.json`, and live repository evidence.
- This command owns the query-backed cognition runtime outputs: `.specify/project-cognition/status.json` and `.specify/project-cognition/project-cognition.db`.
- If the evidence baseline is incomplete or the accepted evidence cannot support graph reconstruction, produce a scan gap report and return to `sp-map-scan`.
- Record accepted and rejected reconstruction evidence as DB/runtime update records and queryable task-local bundle readiness metadata. Treat any raw graph or slice files as compatibility/export artifacts, not runtime truth.
