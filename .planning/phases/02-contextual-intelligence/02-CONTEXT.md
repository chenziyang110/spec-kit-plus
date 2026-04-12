# Phase 2: Contextual Intelligence - Context

**Gathered:** 2026-04-12
**Status:** Ready for planning

<domain>
## Phase Boundary
This phase focuses on the "intelligence" part of the debugger. It enables the agent to automatically ingest Spec Kit artifacts (`spec.md`, `plan.md`, `tasks.md`) and git history to prioritize its search space. It also defines the structured gathering of symptoms and the "No Fix Without Proof" gate.

## Success Criteria
1. Agent automatically ingests core artifacts for the current feature phase.
2. Agent identifies "Recently Modified Files" using git/task history.
3. Agent enforces a mandatory reproduction script/test.
4. Investigation results are logged with "Evidence" and "Eliminated Theories".
</domain>

<decisions>
## Implementation Decisions

### Context Loading
- Automatically load `spec.md`, `plan.md`, and `tasks.md` for the current feature phase when starting an investigation.
- If multiple features are in progress, prioritize the one most recently updated in `tasks.md`.

### Search Space Prioritization
- Analyze the last 5-10 commits to identify recently changed files.
- Cross-reference these changes with the files listed in the `files_modified` section of relevant `plan.md` files.

### Investigation Protocol
- **Reproduction First**: Transition from "Gather" to "Investigate" ONLY after a reproduction test or script is verified to fail.
- **Hypothesis Log**: Every investigation turn MUST start with an update to the `Current Focus` in the debug file, stating the current hypothesis and test.

### Claude's Discretion
- The exact git command used for history analysis.
- The threshold for "large artifact" summarization.
</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/specify_cli/codex_team/auto_dispatch.py`: `parse_tasks_markdown` can be reused or adapted to read `tasks.md`.
- `src/specify_cli/debug/graph.py`: The `DebugGraphState` and node structure from Phase 1.

### established patterns
- Use of `pydantic-graph` for state management.
- Persistence to `.planning/debug/*.md`.
</code_context>

<specifics>
## Specific Ideas
- Integrate with the `notify-hook` if the investigation requires team-level context.
</specifics>

<deferred>
## Deferred Ideas
- Multi-model routing (deferred to Phase 4 or v2).
</deferred>

---
*Phase: 02-contextual-intelligence*
*Context gathered: 2026-04-12 via Smart Discuss*
