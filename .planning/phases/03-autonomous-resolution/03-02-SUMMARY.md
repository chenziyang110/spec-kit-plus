---
phase: 03-autonomous-resolution
plan: 02
subsystem: debug-workflow
tags: [verification, tooling, autonomous-loop]
requires: [SYS-03, SYS-04, TOL-01]
provides: [autonomous-fix-loop]
affects: [src/specify_cli/debug/graph.py, src/specify_cli/debug/utils.py, tests/test_debug_graph.py, tests/test_debug_graph_nodes.py]
tech-stack: [pytest, subprocess, pydantic-graph]
key-files: [src/specify_cli/debug/graph.py, src/specify_cli/debug/utils.py, tests/test_debug_graph.py, tests/test_debug_graph_nodes.py]
decisions:
  - "Use shell-backed command execution plus scoped pytest target resolution to drive autonomous verification"
  - "Prefer changed test files for feature validation before falling back to the broader tests/ directory"
metrics:
  duration: 20m
  completed_date: "2026-04-13"
---

# Phase 03 Plan 02: Autonomous Fixing & Verification Summary

## One-liner
Implemented the autonomous fix-to-verify loop, exposed the filesystem and command helpers it depends on, and aligned the graph tests with the real verification flow.

## Key Changes
### Execution Helpers
- Added `run_command`, `read_file`, and `edit_file` helpers in `src/specify_cli/debug/utils.py`.
- Exposed those helpers directly from the graph module so investigation, fixing, and verification logic can invoke them consistently.

### Autonomous Verification Loop
- Updated `FixingNode` to advance into verification as soon as a fix is recorded in state.
- Updated `VerifyingNode` to rerun the stored reproduction command, choose the most relevant pytest targets, and record evidence for each verification attempt.
- Failed verification now increments `fail_count` and routes back to investigation until the Phase 03 safety gate threshold is reached.

### Test Coverage
- Modernized `tests/test_debug_graph.py` so it validates the current Phase 03 behavior without recursively invoking nested `pytest` sessions.
- Expanded the graph-node test coverage around reproduction execution, changed-file test targeting, fallback project test targeting, and failure evidence capture.

## Deviations from Plan
- Reused `run_command()` for search/test orchestration instead of adding a separate symbol-search helper API. The helper now covers both command execution and repository search workflows.

## Known Stubs
None.

## Self-Check: PASSED
- [x] All tasks executed
- [x] Phase-scoped tests pass
- [x] Deviations documented
- [x] SUMMARY.md created
- [x] Verification inputs are ready for phase-level verification
