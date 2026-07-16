{{spec-kit-include: ../common/user-input.md}}

## Objective

Perform a read-only analysis pass that checks whether the current spec, context, plan, and task artifacts still agree strongly enough to support execution.

## Context

- Primary inputs: `spec.md`, `context.md`, `plan.md`, `tasks.md`, passive learning files, the task-local project cognition query bundle with readiness and returned `minimal_live_reads`, and the smallest workflow-local state files needed for the touched area.
- Treat `spec-contract.json`, `plan-contract.json`, and `task-index.json` as the phase authorities. When delegation occurred, inspect the compact `planning/lane-manifest.json` or `task-generation/lane-manifest.json` and only the accepted lane results needed to verify downstream consumption. Read clarification evidence only when analysis routes back to clarification.
- The constitution remains the highest local authority for this analysis surface.
- This command produces findings only; it does not rewrite the artifact set.

## Process

- Load the minimum artifact context needed to evaluate the current request.
- Compare the planning artifacts for drift, ambiguity, missing constraints, and boundary-guardrail gaps.
- Verify every accepted delegated lane result named by a compact manifest was consumed into the downstream canonical contract rather than only preserved on disk.
- Classify findings by severity and report how they should feed back into the workflow.

## Output Contract

- Emit a structured analysis report with concrete findings, severity, and recommended remediation lanes.
- Keep the result non-destructive and explicit about what command should handle each class of issue.
- Do not silently fix artifacts from inside `/sp-analyze`.

## Guardrails

- Stay read-only.
- Treat constitution conflicts as critical rather than negotiable.
- Do not rely on stale or insufficient project cognition query coverage when the runtime should inform the analysis.
