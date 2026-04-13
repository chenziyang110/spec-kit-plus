# Phase 3: Autonomous Resolution - Context

**Gathered:** 2026-04-12
**Status:** Ready for planning

<domain>
## Phase Boundary
This phase focuses on the "action" part of the debugger. It implements the secure tools required to read/edit code and execute tests. It also defines the autonomous resolution flow: verifying the bug, applying the fix, and validating the result with a safety gate for human intervention.

## Success Criteria
1. Agent creates and verifies a failing reproduction script/test.
2. Agent autonomously applies fixes to source code.
3. Agent validates fixes against reproduction and feature-level tests.
4. Agent triggers HITL checkpoints when verification fails repeatedly.
</domain>

<decisions>
## Implementation Decisions

### Reproduction & Verification
- Prefer `pytest` for reproduction tests. Standalone shell scripts are the fallback for environment-level bugs.
- Verification MUST include the reproduction test and all tests within the current feature's directory.

### Autonomous Fixing
- The agent is authorized to edit source code directly once a root cause is confirmed via a failing reproduction.
- All edits MUST be minimal and focused strictly on the root cause.

### Safety & HITL
- Implement a `fail_count` tracker in the `FixingNode`.
- If verification fails more than 2 times for the same session, transition to `awaiting_human_verify` with a clear report of what was tried.

### Claude's Discretion
- The specific implementation of the code editing tool (e.g., regex vs. full file rewrite).
- The exact format of the Human-in-the-Loop report.
</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tests/test_debug_graph_nodes.py`: Can be expanded to test the new `Fixing` and `Verifying` nodes.
- `src/specify_cli/debug/graph.py`: The `DebugGraphState` and node structure.

### established patterns
- Use of `subprocess.run` for external command execution.
- Persistence via the `@persist` decorator.
</code_context>

<specifics>
## Specific Ideas
- Use a "Sandbox" environment for test execution if available (not strictly required for v1).
</specifics>

<deferred>
## Deferred Ideas
- Automated Knowledge Base (deferred to v2).
</deferred>

---
*Phase: 03-autonomous-resolution*
*Context gathered: 2026-04-12 via Smart Discuss*
