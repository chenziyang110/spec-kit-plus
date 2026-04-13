# Phase 6: Integration Hardening & Alignment - Context

**Gathered:** 2026-04-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Align repository documentation, CLI-facing skill descriptions, generated integration surfaces, and regression tests with the Milestone 2 collaboration state now implemented for `specify`, `plan`, `tasks`, and `explain`.

</domain>

<decisions>
## Implementation Decisions

### Documentation Truthfulness
- README should describe the repository as having Milestones 1 and 2 partially implemented, not as a Milestone 1-only slice.
- Shared workflow messaging should acknowledge that `specify`, `plan`, `tasks`, and `explain` now share the canonical strategy vocabulary.
- README must continue to isolate `specify team` as a Codex-only runtime surface.

### CLI and Generated Skill Descriptions
- Built-in `SKILL_DESCRIPTIONS` should reflect the expanded collaboration surface for `specify`, `plan`, `tasks`, and `explain`.
- Generated skill/integration tests should verify that shared workflow skills contain the canonical strategy names while still excluding Codex-only runtime wording outside the Codex runtime surfaces.

### Regression Scope
- Use integration tests that initialize projects and inspect generated skills to prove the new shared routing language actually ships.
- Preserve Codex-specific runtime guidance for `implement` while asserting that shared analysis/planning skills stay integration-neutral.

### the agent's Discretion
- Exact wording can stay concise as long as it remains accurate about what is shipped versus what is still future work.
- Additional regression assertions can be grouped into existing integration test files rather than creating new suites.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- README already has a dedicated orchestration section and Codex runtime guidance section.
- `src/specify_cli/__init__.py` centralizes built-in skill descriptions.
- `tests/integrations/test_cli.py`, `tests/integrations/test_integration_codex.py`, and `tests/test_extension_skills.py` already validate generated skill surfaces and CLI descriptions.

### Established Patterns
- Shared workflow guarantees are tested by reading generated `SKILL.md` files after `specify init`.
- Codex-only runtime wording is allowed in `implement` for Codex but should not leak into shared analysis/planning skills or non-Codex surfaces.
- README documentation is covered by targeted regression tests in `tests/codex_team/`.

### Integration Points
- README.md
- src/specify_cli/__init__.py
- tests/integrations/test_cli.py
- tests/integrations/test_integration_codex.py
- tests/test_extension_skills.py
- tests/codex_team/test_release_scope_docs.py

</code_context>

<specifics>
## Specific Ideas

- Add one integration test that opens `sp-specify`, `sp-plan`, `sp-tasks`, and `sp-explain` after init and checks for shared strategy language.
- Keep `sp-implement` as the only place where Codex runtime escalation wording remains expected.

</specifics>

<deferred>
## Deferred Ideas

- Runtime maturity for `implement` and `debug` remains future work.
- Additional integrations beyond the current first adapter set remain future work.

</deferred>
