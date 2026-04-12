# Phase 1: Foundation & Resumability - Context

**Gathered:** 2026-04-12
**Status:** Ready for planning
**Source:** Research Phase

<domain>
## Phase Boundary
This phase focuses on the structural foundation of the `sp-debug` feature. It delivers the persistent state machine and the CLI entry point. It does NOT include the actual bug investigation tools or context ingestion (those are Phase 2 and 3).

## Success Criteria
1. User can invoke `sp-debug` from the CLI.
2. Investigation state is persisted to `.planning/debug/[slug].md`.
3. state machine flow (Gather -> Investigate -> Fix -> Verify) is established.
4. Auto-resume works for interrupted sessions.
</domain>

<decisions>
## Implementation Decisions

### Workflow Engine
- Use **pydantic-graph** to manage state transitions.
- Nodes MUST correspond to the "Gather -> Investigate -> Fix -> Verify" stages.

### Persistence
- Format: **Markdown with YAML frontmatter**.
- Frontmatter MUST include: `status`, `trigger`, `created`, `updated`, and the current node ID.
- Sections: `## Current Focus`, `## Symptoms`, `## Eliminated`, `## Evidence`, `## Resolution`.
- Update rule: The file MUST be updated before any external tool action or state transition.

### CLI Integration
- Entry point: `specify debug` (or `sp-debug` as alias).
- Argument: Optional bug description (string).
- Logic: If description provided -> start new session. If empty -> look for most recent unfinished file in `.planning/debug/`.

### Claude's Discretion
- Specific slug generation logic (e.g., timestamp + keyword).
- Exact YAML schema for graph state serialization.
</decisions>

<canonical_refs>
## Canonical References
- `.planning/research/SUMMARY.md` -> Core architecture recommendation.
- `.planning/REQUIREMENTS.md` -> FND-01, FND-02, FND-03 requirements.
- `templates/debug.md` -> The structure for the persistence file.
</canonical_refs>

<specifics>
## Specific Ideas
- Use a "Checkpoint" mechanism to save state after each successful node transition.
</specifics>

---
*Phase: 01-foundation-resumability*
*Context gathered: 2026-04-12 via Research*
