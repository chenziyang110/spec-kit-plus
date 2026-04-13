# Phase 5: Tasks & Explain Collaboration Routing - Context

**Gathered:** 2026-04-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Apply the shared orchestration policy to `tasks` and `explain` so task generation can choose a collaboration strategy before decomposition work begins, and artifact explanation can remain conservative by default while still supporting justified cross-check fan-out.

</domain>

<decisions>
## Implementation Decisions

### Tasks Workflow Contract
- Reuse the same canonical strategy names and fallback order already used by `implement`, `specify`, and `plan`.
- Limit `tasks` collaboration lanes to story and phase decomposition, dependency graph analysis, and write-set / parallel-safety analysis.
- Require join points before writing `tasks.md` and before emitting canonical parallel batches and join points.

### Explain Workflow Contract
- Default `explain` to `single-agent` unless the artifact genuinely benefits from supporting cross-check lanes.
- Limit explain collaboration lanes to primary artifact reading and supporting artifact cross-checks.
- Require the final explanation to converge at one join point before rendering the terminal presentation.

### Surface Isolation
- Keep shared workflow templates integration-neutral.
- Continue treating Codex runtime wording as compatibility-layer guidance, not shared workflow copy.

### the agent's Discretion
- Exact wording can follow the existing explain/tasks template tone so long as the conservative routing policy remains explicit.
- Additional tests can be added in the existing template/TUI contract files where they best fit the repository’s current structure.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/specify_cli/orchestration/policy.py` already provides the generic decision order.
- `templates/commands/tasks.md` already describes write sets, join points, and parallel batches.
- `templates/commands/explain.md` already has a stage-aware TUI contract that can be extended with routing guidance.

### Established Patterns
- Shared workflow routing language is tested in `tests/test_alignment_templates.py`.
- Explain TUI expectations are covered in `tests/test_tui_visual_contract.py` and mirrored through generated-skill checks in `tests/test_extension_skills.py`.

### Integration Points
- `templates/commands/tasks.md`
- `templates/commands/explain.md`
- `tests/test_alignment_templates.py`
- `tests/test_tui_visual_contract.py`
- `tests/test_extension_skills.py`
- `tests/orchestration/test_policy.py`

</code_context>

<specifics>
## Specific Ideas

- `tasks` should explicitly record why it stayed `single-agent` or escalated, using the same reasoning vocabulary as the other workflows.
- `explain` should say clearly when collaboration is not justified and why the explanation remained single-agent.

</specifics>

<deferred>
## Deferred Ideas

- CLI/init messaging and generated-skill integration hardening belong to Phase 6.
- Runtime maturity for `implement` and `debug` remains deferred to later milestones.

</deferred>
