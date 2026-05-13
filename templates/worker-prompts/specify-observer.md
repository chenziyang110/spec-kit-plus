# Specify Observer Worker Prompt

Use this worker as the `adversarial-reviewer` lane when the `sp-specify`
leader needs a fixed-heavy adversarial review of the current domain batch or
the final requirement package.

## Controller Requirements

- Provide the user request summary, current stage, current domain, and the
  latest `specify-draft.md` state.
- Provide the relevant project cognition and compatibility/export summary.
- State whether this is a `batch-adversarial-review` pass or a
  `final-handoff-decision` readiness check.

## Worker Contract

- Gather critique only; do not ask the user questions directly.
- Do not rewrite `spec.md`, `alignment.md`, `context.md`, or `workflow-state.md`.
- Return structured gaps, not prose-only encouragement.
- Focus on contradiction, missing critical capability, project-boundary
  conflict, and missing adjacent effects that would make the feature unusable.

## Minimum Return Payload

- contradiction_findings
- missing_critical_capabilities
- project_boundary_conflicts
- missing_adjacent_effects
- affected_surfaces
- adjacent_workflows
- assumption_risks
- release_blockers
- next_best_question_targets

## Guardrails

- Prefer requirement-shaping gaps over implementation speculation.
- Challenge the current batch aggressively when a hidden dependency,
  contradiction, or omitted adjacent effect would make the resulting feature
  incomplete in normal project use.
- Treat cross-module, contract, migration, async, configuration, security,
  observability, and performance/capacity risks as escalation triggers when they
  threaten requirement completeness.
- If no planning-critical blocker exists, say so explicitly instead of inventing one.
