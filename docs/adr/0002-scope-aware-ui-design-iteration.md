# ADR-0002: Scope-aware UI design iteration

**Date**: 2026-08-12
**Status**: accepted
**Deciders**: Project maintainers

## Context

Immutable change-local UI contracts prevent silent edits, but the first
registration model retires an entire prior change whenever a successor overlaps
it. A mobile or child-route refinement can therefore erase still-valid desktop
or sibling-route guidance. Consumers also need a deliberate way to inspect,
compare, and adopt a successor without resolving an implicit latest value.

## Decision

Registered UI changes remain immutable snapshots. `design iterate` creates a
digest-pinned successor, registration subtracts only the intersecting scope from
the prior change, and a prior record becomes fully superseded only when every
declared scope root is covered. `design resolve` discovers active candidates,
`design diff` compares their semantic contracts, and `design adopt` records an
append-only, CAS-guarded consumer binding; none of these commands silently
retarget existing work.

## Alternatives Considered

### Alternative 1: Supersede the entire prior change

- **Pros**: Simple status model and one active successor.
- **Cons**: A narrow refinement invalidates unrelated rules and platforms.
- **Why not**: It makes partial UI iteration unsafe.

### Alternative 2: Generate one merged global design document

- **Pros**: Consumers read one effective file.
- **Cons**: Reintroduces mutable global authority and precedence ambiguity.
- **Why not**: It reverses ADR-0001 and hides which approval supplied a rule.

### Alternative 3: Resolve and adopt the newest matching change automatically

- **Pros**: Minimal consumer workflow.
- **Cons**: Active delivery can change without review and historical builds are
  no longer reproducible.
- **Why not**: Discovery and adoption must remain separate trust boundaries.

## Consequences

### Positive

- A child surface can evolve while its parent and sibling guidance remain valid.
- Every iteration names an exact source contract and digest.
- Consumers retain their old pin until an explicit, revision-guarded adoption.
- Semantic comparison exposes scope, decision, and handoff-contract changes.

### Negative

- The index must retain scope exclusions and adoption history.
- Broad consumers may need multiple bounded task-level bindings instead of one
  synthesized global contract.
- Go and Python design command surfaces must remain behaviorally aligned.

### Risks

- **Unrepresentable complements**: store excluded subtrees rather than inventing
  a synthetic `parent minus child` scope string.
- **Ambiguous broad work**: return all intersecting active candidates and require
  the consumer to split scope or explicitly bind each bounded unit.
- **Stale adoption**: require the expected current change ID and exact binding
  artifact digest before appending a new adoption receipt.
