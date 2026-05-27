# sp-discussion Adaptive Question Pack Design

## Summary

`sp-discussion` should use an adaptive question pack instead of a blanket one-question pacing rule.

Each turn keeps one primary question, but may include up to two optional follow-up questions when the questions are same-topic, low-risk, and do not lock major boundaries. Boundary ambiguity, evidence conflicts, cross-project target selection, handoff readiness, destructive or lifecycle consequences, and major product trade-offs still require exactly one question.

Multiple-choice questions must include a recommended option and a short recommendation reason.

## Scope

- Update the discussion command template.
- Update the discussion shell partial summary.
- Update the discussion state template so resumable state can carry a question pack.
- Update focused template and integration contract tests.

## Non-Goals

- Do not add a runtime state machine.
- Do not change handoff artifacts.
- Do not change `sp-specify`.
- Do not broaden workflow routing.
