# Requirements: sp-debug

This document defines the scoped requirements for the `sp-debug` systematic debugging feature in `spec-kit-plus`.

## v1 Requirements

### Foundation & Persistence (FND)
- [x] **FND-01**: Implement investigation graph using `pydantic-graph` to manage "Gather -> Investigate -> Fix -> Verify" states.
- [ ] **FND-02**: Implement a Markdown-based persistence handler that serializes the current graph state, hypothesis, and evidence to `.planning/debug/[slug].md`.
- [ ] **FND-03**: Support "Resume Mode": When `sp-debug` is called without arguments, it automatically detects the most recent unfinished session from `.planning/debug/` and restores its full state.
- [x] **FND-04**: Implement a "No Fix Without Proof" gate: The agent must verify the bug with a reproduction script or failing test before attempting a fix.

### Context Awareness (CTX)
- [x] **CTX-01**: Automatically load `constitution.md`, `spec.md`, `plan.md`, and `tasks.md` during the investigation phase to provide system-level context.
- [x] **CTX-02**: Identify "Recently Modified Files" by analyzing git history or Spec Kit task logs to prioritize the search space.
- [x] **CTX-03**: Integrate with `ROADMAP.md` to understand which feature phase the current bug belongs to.

### Systematic Investigation (SYS)
- [x] **SYS-01**: "Gather" Node: Ask clarifying questions to capture symptoms (Expected vs Actual) and reproduction steps.
- [x] **SYS-02**: "Investigate" Node: Formulate and test hypotheses one by one, recording "Evidence" and "Eliminated Theories" in the debug file.
- [ ] **SYS-03**: "Fix" Node: Propose and apply minimal changes based on the confirmed root cause.
- [ ] **SYS-04**: "Verify" Node: Re-run reproduction scripts and phase-level tests to prove the fix works and no regressions were introduced.

### Tools & Integration (TOL)
- [ ] **TOL-01**: Provide `sp-debug` with tools to read files, search for symbols, run terminal commands, and edit code.
- [ ] **TOL-02**: Implement a Human-in-the-Loop (HITL) checkpoint when verification fails or a decision requires user confirmation.
- [ ] **TOL-03**: Register the `/sp-debug` command in the `specify` CLI.

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| FND-01 | Phase 1 | Complete |
| FND-02 | Phase 1 | Pending |
| FND-03 | Phase 1 | Pending |
| FND-04 | Phase 3 | Complete |
| CTX-01 | Phase 2 | Complete |
| CTX-02 | Phase 2 | Complete |
| CTX-03 | Phase 2 | Complete |
| SYS-01 | Phase 2 | Complete |
| SYS-02 | Phase 2 | Complete |
| SYS-03 | Phase 3 | Pending |
| SYS-04 | Phase 3 | Pending |
| TOL-01 | Phase 3 | Pending |
| TOL-02 | Phase 3 | Pending |
| TOL-03 | Phase 1 | Pending |

## v2 Requirements (Deferred)
- [ ] **OPT-01**: Automated Knowledge Base: Log resolved bugs to a persistent database to speed up future diagnosis of similar symptoms.
- [ ] **OPT-02**: Multi-Model Routing: Use cheaper models for gathering/summarization and expensive models (Claude 3.5 Sonnet) for core investigation.
- [ ] **OPT-03**: Deep Tracing: Integrate Logfire for real-time observability of the agent's reasoning process.

## Out of Scope
- General code refactoring outside the verified root cause area.
- Automatic patching of external library dependencies (vendor code).

---
*Last updated: 2026-04-12 after initialization*
