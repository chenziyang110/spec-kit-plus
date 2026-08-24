# ADR-0002: Retire `DESIGN.md` from the active workflow

**Date**: 2026-08-24
**Status**: accepted
**Deciders**: Project maintainers
**Supersedes**: The filename and legacy-root compatibility portions of ADR-0001

## Context

`sp-design` serves one bounded requirements iteration. Keeping either a root
`DESIGN.md` compatibility artifact or a change-local file with that global-looking
name suggests an evergreen project authority that the workflow no longer owns.

## Decision

- The canonical human-readable contract is
  `.specify/design/changes/<UD-ID>/design-change.md`.
- `specify-runtime design change` and `design iterate` create only that
  change-local contract and its workspace artifacts.
- Root `DESIGN.md` is no longer installed, registered, discovered, or accepted
  as workflow truth.
- Durable cross-change invariants live in `.specify/memory/project-rules.md`.
  Existing-product visual authority comes from explicitly cited live UI,
  components, and tokens.
- `design-contract.json` remains the deterministic downstream export paired
  with the registered change-local Markdown contract.

## Consequences

- Classic and Advanced workflows, runtime implementations, artifact routing,
  task packets, and documentation all use `design-change.md`.
- Stale generated UI artifacts are regenerated into the current contract; the
  runtime does not infer or silently adopt a root design document.
- Historical documents may still describe the former filename, but they are not
  active workflow surfaces.
