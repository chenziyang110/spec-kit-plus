{{spec-kit-include: ../common/user-input.md}}

## Objective

Create or update the project constitution as the authoritative rule layer for downstream specification, planning, and execution work.

## Context

- Primary inputs: the current constitution, the user's requested principle changes, and any repository context needed to derive missing values.
- The constitution must stay synchronized with dependent templates and guidance files.
- Versioning and governance metadata are part of the contract, not optional decoration.

## Process

- Load the current constitution and identify unresolved placeholders or requested changes.
- Derive the right version bump and updated governance metadata.
- Rewrite the constitution and propagate any downstream template or docs updates required by the amendment.

## Output Contract

- Write a finalized constitution with a sync-impact report.
- Keep dependent templates and guidance aligned with the updated principles.
- Surface any follow-up items if a value must remain intentionally deferred.

## Guardrails

- Do not leave unexplained placeholders behind.
- Respect the semantic-versioning rules for constitution changes.
- Do not update downstream guidance partially; either sync it or report it as pending.
