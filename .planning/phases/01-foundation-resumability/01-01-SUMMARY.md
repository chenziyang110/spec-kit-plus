---
phase: 01-foundation-resumability
plan: 01
subsystem: sp-debug
tags: [pydantic-graph, state-machine, foundations]
requires: []
provides: [FND-01]
affects: [pyproject.toml]
tech-stack: [pydantic-graph, pydantic-ai]
key-files: [src/specify_cli/debug/schema.py, src/specify_cli/debug/graph.py, tests/test_debug_graph.py]
decisions:
  - Use pydantic-graph for the investigation lifecycle as planned.
  - Mapping schema fields directly to the debug template frontmatter and sections.
metrics:
  duration: 15m
  completed_date: 2026-04-12
---

# Phase 01 Plan 01: Debug Graph Foundations Summary

Established the core pydantic-graph structure for the systematic debugging engine, including shared state, node definitions, and skeleton transition logic.

## Key Accomplishments

- **Dependency Setup:** Added `pydantic-ai` and `pydantic-graph` to `pyproject.toml`.
- **State Definition:** Created `DebugGraphState` in `src/specify_cli/debug/schema.py` which mirrors the standard debugging Markdown template.
- **Node Architecture:** Defined 6 core nodes (`GatheringNode`, `InvestigatingNode`, `FixingNode`, `VerifyingNode`, `AwaitingHumanNode`, `ResolvedNode`) in `src/specify_cli/debug/graph.py`.
- **Lifecycle Flow:** Implemented and verified the transition logic using TDD. The graph now correctly moves through the investigation stages based on the internal state (e.g., presence of root cause or fix).

## Deviations from Plan

- **[Rule 3 - Blocking Issue] Missing dependencies for verification**
  - **Found during:** Task 2 verification.
  - **Issue:** `pydantic-graph` was not installed in the execution environment, preventing verification scripts from running.
  - **Fix:** Manually installed `pydantic-ai` and `pydantic-graph` via pip.
  - **Files modified:** N/A (Environment change).
  - **Commit:** N/A.

- **[Rule 1 - Bug] Incorrect GraphRunContext instantiation in tests**
  - **Found during:** Task 3 TDD (RED phase).
  - **Issue:** `GraphRunContext` requires keyword arguments `state` and `deps`, but was called with positional arguments in the first test draft.
  - **Fix:** Updated test code to use `GraphRunContext(state=state, deps=None)`.
  - **Files modified:** `tests/test_debug_graph.py`.
  - **Commit:** `test(01-01): add failing test for debug graph transitions` (Corrected during RED phase).

## Known Stubs

- **Node Implementation Stubs:** The `run()` methods for all nodes currently only handle transition logic. The actual "work" (gathering symptoms via AI, applying fixes, etc.) is stubbed with simple state checks to be implemented in future plans.
- **AwaitingHumanNode:** Currently returns `End` and is not fully wired into the flow yet as it's intended for human-in-the-loop interactions.

## Self-Check: PASSED
