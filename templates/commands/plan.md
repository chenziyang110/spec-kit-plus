---
description: Use when the current specification package is ready for implementation planning and you need design artifacts before task breakdown or coding.
workflow_contract:
  when_to_use: The current spec package is ready for design work, but implementation should not start until explicit planning artifacts exist.
  primary_objective: Produce the planning artifact set that turns specification intent into an implementation-ready architecture and execution approach.
  primary_outputs: '`plan.md`, `research.md`, `quickstart.md`, `plan-contract.json`, and `workflow-state.md` under the active `FEATURE_DIR`; `data-model.md` and `contracts/` when the feature scope demands them; `planning/handoffs/<lane-id>.json`, `planning/evidence-index.json`, and `planning/checkpoints.ndjson` only when delegated planning lanes are used.'
  default_handoff: '/sp.tasks for decomposition; /sp.checklist remains optional for requirements-quality review, not a default handoff.'
handoffs:
  - label: Create Tasks
    agent: sp.tasks
    prompt: Break the plan into tasks
    send: true
  - label: Create Checklist
    agent: sp.checklist
    prompt: Create a checklist for the following domain...
scripts:
  sh: scripts/bash/setup-plan.sh --json
  ps: scripts/powershell/setup-plan.ps1 -Json
agent_scripts:
  sh: scripts/bash/update-agent-context.sh __AGENT__
  ps: scripts/powershell/update-agent-context.ps1 -AgentType __AGENT__
---

{{spec-kit-include: ../command-partials/plan/shell.md}}

{{spec-kit-include: ../command-partials/common/senior-consequence-analysis-gate.md}}

[AGENT] For project-cognition-backed semantic intake, routing, audit, resume, or final-claim gates, read `references/semantic-work-contract.md`.

{{spec-kit-include: ../command-partials/common/adaptive-execution.md}}

## Main Flow

1. Resolve the feature directory, create or resume `workflow-state.md`, and keep `phase_mode: design-only`; do not edit source/runtime/test files.
2. Read `spec.md`, `alignment.md`, `context.md`, optional handoffs, `.specify/memory/constitution.md`, project rules, and relevant learning files before synthesizing artifacts.
3. Preserve complete-first scope: do not split confirmed scope into MVP, future-work slices, `v1/v2`, `P0/P1`, or a smaller delivery unless the user confirmed the deferral contract.
4. Generate `research.md`, conditional `data-model.md` and `contracts/`, required `quickstart.md`, `plan.md`, `plan-contract.json`, and `workflow-state.md` according to the detailed references.
5. Use `choose_subagent_dispatch(command_name="plan", snapshot, workload_shape)` only for isolated planning lanes; delegated lanes must write `planning/handoffs/<lane-id>.json`, `planning/evidence-index.json`, and `planning/checkpoints.ndjson`.
6. Add `Implementation Constitution`, `Reference Fidelity Inputs`, `Dispatch Compilation Hints`, `Review-Risk Notes`, and `Input Risks From Alignment` when their triggers are present.
7. Re-check constitution, complexity, risk, locked planning decisions, and deep-research `PH-###` traceability before recommending `{{invoke:tasks}}`.

## Detailed References

Read [Reference index](references/INDEX.md) before applying detailed contracts.

- [spec package intake](references/spec-package-intake.md)
- [research and design lanes](references/research-and-design-lanes.md)
- [data model contracts and quickstart](references/data-model-contracts-and-quickstart.md)
- [constitution risk and complexity](references/constitution-risk-and-complexity.md)
- [subagent dispatch](references/subagent-dispatch.md)
- [plan contract fields](references/plan-contract-fields.md)
