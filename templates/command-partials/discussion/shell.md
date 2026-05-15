{{spec-kit-include: ../common/user-input.md}}

## Objective

Drive a resumable product and technical discussion that matures a rough idea into requirements and implementation options before formal specification.

## Context

- Primary inputs: the user's idea, the current discussion session under `.specify/discussions/<slug>/`, passive project memory, and project cognition when the discussion reaches source-grounded technical judgment.
- `discussion-state.md` is the durable session state source of truth.
- `sp-discussion` is upstream of `sp-specify`; it does not create feature branches or write formal feature artifacts.

## Process

- Create or resume the discussion session.
- Ask one high-impact question at a time.
- Preserve key decisions in `discussion-log.md`.
- Keep `requirements.md`, `technical-options.md`, `project-context.md`, and `open-questions.md` current.
- Generate `handoff-to-specify.md` and `handoff-to-specify.json` only after explicit user request.

## Output Contract

- Maintain the independent discussion state and artifacts under `.specify/discussions/<slug>/`.
- Provide 2-3 project-grounded technical options when implementation strategy affects the requirement.
- Report unresolved questions honestly instead of forcing planning readiness.
- When explicit handoff is requested, write both `handoff-to-specify.md` and `handoff-to-specify.json` with a Must-Preserve Ledger.
- Do not mark handoff ready if a confirmed goal, non-goal, decision, critical reference, trade-off rationale, or blocking question is missing from the ledger.
- Preserve `coverage_status`, `planning_gate_status`, `hard_unknown_count`, and `open_conflict_count` for the downstream fidelity gate.

## Guardrails

- Do not edit source code or tests.
- Do not create feature branches or feature directories.
- Do not automatically invoke or route into `sp-specify`.
- Do not make project-specific technical claims before the staged cognition gate passes.
