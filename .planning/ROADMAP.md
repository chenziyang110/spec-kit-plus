# Roadmap: sp-debug

## Phases

- [ ] **Phase 1: Foundation & Resumability** - Establish the persistent, graph-based investigation loop and CLI entry point.
- [ ] **Phase 2: Contextual Intelligence** - Enable the agent to ingest Spec Kit artifacts and prioritize search space.
- [ ] **Phase 3: Autonomous Resolution** - Implement verification-led fixing with secure code and test tools.

## Phase Details

### Phase 1: Foundation & Resumability
**Goal**: Establish the `sp-debug` command with a persistent investigation graph.
**Depends on**: None
**Requirements**: FND-01, FND-02, FND-03, TOL-03
**Success Criteria** (what must be TRUE):
  1. User can invoke `sp-debug` from the CLI and initialize a new investigation session.
  2. Investigation state (nodes, hypotheses, evidence) is persisted to a human-readable Markdown file in `.planning/debug/`.
  3. Running `sp-debug` after an interruption automatically restores the previous state and resumes from the last active node.
  4. The investigation loop follows a structured state machine (Gather -> Investigate -> Fix -> Verify) using `pydantic-graph`.
**Plans**: 3 plans
- [ ] 01-01-PLAN.md — Foundation & State Machine (Infrastructure, Node schema, transition logic)
- [ ] 01-02-PLAN.md — Markdown Persistence (Serialization, slug logic, graph integration)
- [ ] 01-03-PLAN.md — CLI & Resume (Command registration, session lookup, end-to-end flow)

### Phase 2: Contextual Intelligence
**Goal**: Empower the agent to understand the system state and recent changes using project artifacts.
**Depends on**: Phase 1
**Requirements**: CTX-01, CTX-02, CTX-03, SYS-01, SYS-02
**Success Criteria** (what must be TRUE):
  1. The agent automatically ingests `spec.md`, `plan.md`, `tasks.md`, and `ROADMAP.md` upon starting an investigation to build system context.
  2. The agent identifies and prioritizes "Recently Modified Files" based on git history and Spec Kit task logs.
  3. The agent captures "Expected vs Actual" symptoms through structured user interaction during the "Gather" phase.
  4. The agent records "Eliminated Theories" in the debug log to ensure non-circular reasoning and provide a clear investigation audit trail.
**Plans**: TBD

### Phase 3: Autonomous Resolution
**Goal**: Enable the agent to verify, fix, and validate bugs using secure tools and verification gates.
**Depends on**: Phase 2
**Requirements**: FND-04, SYS-03, SYS-04, TOL-01, TOL-02
**Success Criteria** (what must be TRUE):
  1. The agent creates and executes a reproduction script or failing test that proves the existence of the reported bug.
  2. The agent adheres to a "No Fix Without Proof" gate, refusing to modify code until a reproduction failure is observed.
  3. The agent autonomously modifies source code and executes relevant tests to verify the resolution and check for regressions.
  4. The agent triggers a Human-in-the-Loop (HITL) checkpoint if automated verification fails or if a proposed fix requires user confirmation.
**Plans**: TBD

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation & Resumability | 0/3 | In progress | - |
| 2. Contextual Intelligence | 0/1 | Not started | - |
| 3. Autonomous Resolution | 0/1 | Not started | - |
