{{spec-kit-include: ../common/user-input.md}}

## Objective

Build or refresh the canonical runtime handbooks from a completed scan package.

## Context

- Primary inputs: `.specify/project-map/map-scan.md`, `.specify/project-map/coverage-ledger.json`, `.specify/project-map/coverage-ledger.md`, `.specify/project-map/scan-packets/*.md`, `.specify/project-map/map-state.md`, existing handbooks when present, and live repository evidence.
- This command owns the two workflow handbook runtime outputs.
- If the scan package is incomplete or the accepted evidence cannot support workflow-operational handbook content, produce a scan gap report and return to `sp-map-scan`.
- Record accepted/rejected packet evidence in `.specify/project-map/map-state.md` and `.specify/project-map/worker-results/*.json`.
