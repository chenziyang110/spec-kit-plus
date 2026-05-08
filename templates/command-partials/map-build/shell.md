{{spec-kit-include: ../common/user-input.md}}

## Objective

Reconstruct or refresh the graph-native project cognition runtime from a completed evidence baseline.

## Context

- Primary inputs: `.specify/project-cognition/status.json`, `.specify/project-cognition/evidence/`, `.specify/project-cognition/provisional/nodes.json`, `.specify/project-cognition/provisional/edges.json`, `.specify/project-cognition/provisional/observations.json`, and live repository evidence.
- This command owns the graph-native cognition runtime outputs.
- If the evidence baseline is incomplete or the accepted evidence cannot support graph reconstruction, produce a scan gap report and return to `sp-map-scan`.
- Record accepted and rejected reconstruction evidence in `.specify/project-cognition/graph/updates.json` and the refreshed graph artifacts.
