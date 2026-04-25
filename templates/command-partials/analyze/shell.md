{{spec-kit-include: ../common/user-input.md}}

## Objective

Perform a read-only analysis pass that checks whether the current spec, context, plan, and task artifacts still agree strongly enough to support execution.

## Context

- Primary inputs: `spec.md`, `context.md`, `plan.md`, `tasks.md`, passive learning files, and the handbook/project-map set.
- The constitution remains the highest local authority for this analysis surface.
- This command produces findings only; it does not rewrite the artifact set.

## Process

- Load the minimum artifact context needed to evaluate the current request.
- Compare the planning artifacts for drift, ambiguity, missing constraints, and boundary-guardrail gaps.
- Classify findings by severity and report how they should feed back into the workflow.

## Output Contract

- Emit a structured analysis report with concrete findings, severity, and recommended remediation lanes.
- Keep the result non-destructive and explicit about what command should handle each class of issue.
- Do not silently fix artifacts from inside `/sp-analyze`.

## Guardrails

- Stay read-only.
- Treat constitution conflicts as critical rather than negotiable.
- Do not rely on stale or insufficient project-map coverage when the repository map should inform the analysis.
