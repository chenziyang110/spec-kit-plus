# ADR-0001: Change-scoped UI design contracts

**Date**: 2026-08-11
**Status**: accepted
**Deciders**: Project maintainers

## Context

The root `DESIGN.md` currently acts as project baseline, pending proposal,
approved visual direction, and downstream implementation contract. Intentional
UI refactors therefore appear to violate the same document that the refactor
must replace. New approvals also risk becoming an implicit latest global value
instead of an explicitly adopted delivery dependency.

## Decision

Each substantive UI change owns an immutable approved contract at
`.specify/design/changes/<UD-ID>/DESIGN.md`. A metadata-only
`.specify/design/index.json` records scope, lifecycle, relationships, digests,
and consumers; it is not design truth. Consumers pin an exact change path and
digest, while durable project-wide invariants are promoted separately to
`.specify/memory/project-rules.md`. Existing root `DESIGN.md` files remain
read-only legacy baselines during migration.

## Alternatives Considered

### Alternative 1: Continue mutating one root DESIGN.md

- **Pros**: One obvious path and minimal implementation change.
- **Cons**: Conflates baseline and proposal, loses history, and silently changes future consumers.
- **Why not**: It directly causes the conflict this decision must remove.

### Alternative 2: Store DESIGN.md inside each formal feature

- **Pros**: Simple feature ownership and familiar locality.
- **Cons**: Design may precede Specify, span features, or be consumed directly by Quick.
- **Why not**: Feature ownership is narrower than UI-change ownership.

### Alternative 3: Generate a new effective global design document

- **Pros**: Downstream consumers keep reading one synthesized file.
- **Cons**: Recreates mutable global authority and introduces merge/precedence ambiguity.
- **Why not**: The index should resolve exact contracts without becoming another design document.

## Consequences

### Positive

- Intentional redesigns declare bounded deltas and `supersedes` relationships.
- Existing feature and Quick work remains pinned to its approved digest.
- Independent UI changes can coexist without rewriting unrelated design truth.
- Existing approval sidecars, `DS-*`/`DH-*` rows, and visual evidence remain reusable.

### Negative

- Design commands and generated prompts must carry an explicit change ID and path.
- Initialization, artifact classification, documentation, and cross-profile tests require migration.
- Scope overlap and lifecycle transitions need deterministic validation.

### Risks

- **Ambiguous overlap**: block concurrent approved changes that target the same scope unless an explicit relationship resolves order.
- **Legacy drift**: keep root contracts readable but never select them as an implicit latest baseline.
- **Index inflation**: limit the index to metadata; design prose stays in each change workspace.
