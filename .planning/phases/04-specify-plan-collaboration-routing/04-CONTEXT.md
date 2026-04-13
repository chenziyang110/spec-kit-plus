# Phase 4: Specify & Plan Collaboration Routing - Context

**Gathered:** 2026-04-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Extend the shared orchestration policy and adapter model to the `specify` and `plan` workflows so these analysis-first surfaces can make explicit execution-strategy decisions, describe their collaboration lanes, and keep native agent entrypoints primary.

</domain>

<decisions>
## Implementation Decisions

### Workflow Strategy Contract
- Reuse the canonical strategy names already established for `implement`: `single-agent`, `native-multi-agent`, and `sidecar-runtime`.
- Keep the decision order consistent with `src/specify_cli/orchestration/policy.py` so the templates, docs, and tests all describe the same fallback path.
- Record the strategy decision inside the workflow artifacts (`alignment.md` for `specify`, planning output for `plan`) instead of inventing a separate runtime-only status surface.

### Lane Planning
- `specify` should describe collaboration as repository/local context analysis, external references/supporting material analysis, and ambiguity/risk/gap analysis with a join before capability decomposition and final artifact writing.
- `plan` should describe collaboration as research, data model, contracts, and quickstart/validation lanes with joins before constitution/risk re-check and before writing the consolidated plan.
- Both workflows must stay conservative when the work does not justify fan-out.

### Surface Isolation
- Non-Codex integrations must continue to see their native command or skill surfaces as primary.
- Codex-only runtime wording such as `specify team` must stay isolated from shared `specify` and `plan` templates.

### the agent's Discretion
- Exact phrasing can be adjusted to fit existing template style as long as the strategy order, lane purpose, and join-point semantics remain explicit.
- Additional focused regression coverage can be added where it best matches the existing test layout.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/specify_cli/orchestration/policy.py` already defines the shared decision order and reason codes.
- `templates/commands/implement.md` already contains the canonical strategy contract language that can be mirrored onto other workflows.
- `tests/test_alignment_templates.py` is the existing template-contract guardrail for workflow language.

### Established Patterns
- Shared workflow behavior is usually expressed in the command templates rather than a separate Python runtime.
- CLI-visible wording is validated with a mix of template tests and `CliRunner`-based integration tests.
- Codex-specific runtime wording is injected in the Codex integration layer rather than shared templates.

### Integration Points
- Shared templates under `templates/commands/`
- Template contract tests under `tests/test_alignment_templates.py`
- Generic policy coverage under `tests/orchestration/test_policy.py`

</code_context>

<specifics>
## Specific Ideas

- Keep `specify` explicitly analysis-first: choose the execution strategy before capability decomposition and before writing `spec.md` and `alignment.md`.
- Keep `plan` explicitly design-first: choose the execution strategy before research/design fan-out and before writing the implementation plan artifacts.

</specifics>

<deferred>
## Deferred Ideas

- `tasks` and `explain` routing belong to Phase 5.
- CLI/init messaging and generated asset hardening belong to Phase 6.
- Durable runtime maturity for `implement` and `debug` remains in later milestones.

</deferred>
