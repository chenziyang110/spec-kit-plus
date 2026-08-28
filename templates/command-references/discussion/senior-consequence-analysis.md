Trigger: before technical recommendations, handoff-readiness claims, or final claims involving lifecycle or running objects, destructive or security-sensitive behavior, shared state, downstream consumers, compatibility, multiple behaviors, or entrypoint-outcome inheritance.

Purpose: preserve the Senior Consequence Analysis Gate without inflating the discussion entry file, while keeping the gate mandatory for risk-bearing technical advice and handoff/final-claim decisions.

Preserved Contract: when the gate triggers, `sp-discussion` must preserve `CA-###` obligations, the Affected Object Map, State-Behavior Matrix, Dependency Impact Table, Recovery And Validation Contract, Coverage Gaps, and any Entrypoint Outcome Contract obligations; handoff readiness and final claims must not skip this gate.

{{spec-kit-include: ../../command-partials/common/senior-consequence-analysis-gate.md}}
