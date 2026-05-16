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
- When the user explicitly asks to hand off or continue the next stage, write `handoff-assessment.md` first.
- If assessment returns `split-required`, maintain `split-plan.md` as the candidate backlog and generate `handoffs/<candidate_id>-handoff-to-specify.md` and `handoffs/<candidate_id>-handoff-to-specify.json` only after the user selects a stable candidate ID such as `CAND-001` or `CAND-002`.
- Refresh latest selected candidate copy files `handoff-to-specify.md` and `handoff-to-specify.json` together for compatibility.

## Output Contract

- Maintain the independent discussion state and artifacts under `.specify/discussions/<slug>/`.
- Provide 2-3 project-grounded technical options when implementation strategy affects the requirement.
- Report unresolved questions honestly instead of forcing planning readiness.
- Keep `handoff-to-specify.md` and `handoff-to-specify.json` as latest selected candidate copy files, not the only handoff output.
- Keep candidate-specific handoffs under `handoffs/` canonical when split mode is active.

## Guardrails

- Do not edit source code or tests.
- Do not create feature branches or feature directories.
- Do not automatically invoke or route into `sp-specify`.
- Do not make project-specific technical claims before the staged cognition gate passes.
