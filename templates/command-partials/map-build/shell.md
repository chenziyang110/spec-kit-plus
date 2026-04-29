{{spec-kit-include: ../common/user-input.md}}

## Objective

Build or refresh the canonical handbook/project-map atlas from a completed scan package.

## Context

- Primary inputs: `.specify/project-map/map-scan.md`, `.specify/project-map/coverage-ledger.json`, `.specify/project-map/coverage-ledger.md`, `.specify/project-map/scan-packets/*.md`, and the live repository.
- This command owns final atlas outputs and freshness metadata.
- If the scan package is incomplete, produce a scan gap report and return to `sp-map-scan` instead of writing a shallow atlas.
