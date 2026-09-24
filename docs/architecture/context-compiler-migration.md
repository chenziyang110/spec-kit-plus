# Context Compiler Migration Plan

## Phase 1

Introduce the context packet contract without changing existing workflows.

## Phase 2

Add a runtime-owned compiler:

```text
task state + workflow + permissions
          |
          v
 context packet
          |
          v
 agent execution
```

## Phase 3

Move deterministic assembly out of prompt instructions:

- state lookup
- artifact selection
- acceptance extraction
- capability selection

## Safety

The compiler must not:

- grant permissions
- replace acceptance
- invent missing facts
- become an alternative source of truth

## First target

Quick workflow, because it already has explicit task contracts, packets and acceptance gates.
