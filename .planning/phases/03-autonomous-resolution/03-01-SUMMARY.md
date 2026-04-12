---
phase: 03-autonomous-resolution
plan: 01
subsystem: debug-workflow
tags: [schema, persistence, graph, gate]
requires: [FND-04]
provides: [SYS-01]
affects: [src/specify_cli/debug/graph.py, src/specify_cli/debug/schema.py, src/specify_cli/debug/persistence.py]
tech-stack: [pydantic, pydantic-graph, pytest]
key-files: [src/specify_cli/debug/schema.py, src/specify_cli/debug/persistence.py, src/specify_cli/debug/graph.py]
decisions:
  - "Enforce reproduction_verified in GatheringNode to ensure bug reproducibility before investigation"
  - "Track fail_count in Resolution for future safety gate logic"
metrics:
  duration: 15m
  completed_date: "2026-04-12"
---

# Phase 03 Plan 01: Investigation Refinement Summary

## One-liner
Refined the investigation workflow by enforcing a "No Fix Without Proof" gate in `GatheringNode` and adding failure tracking to the state.

## Key Changes
### Schema and Persistence
- Added `fail_count` to the `Resolution` model to track failed verification attempts.
- Added `reproduction_command` to the `Symptoms` model to capture how the bug is reproduced.
- Updated `MarkdownPersistenceHandler` to correctly serialize and deserialize these new fields in the debug markdown file.

### Enforced Reproduction Gate
- Modified `GatheringNode.run` to check if `reproduction_verified` is set to `True`.
- If not verified, the session stays in `GATHERING` status and sets `next_action` to prompt the agent to create and verify a reproduction script.
- This ensures that investigation and fixing cannot proceed without a verified failing test.

## Deviations from Plan
None - plan executed exactly as written.

## Known Stubs
None.

## Self-Check: PASSED
- [x] All tasks executed
- [x] Each task committed individually
- [x] All deviations documented
- [x] SUMMARY.md created
- [x] COMMITS verified
