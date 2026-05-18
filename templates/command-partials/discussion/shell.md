{{spec-kit-include: ../common/user-input.md}}

## Objective

Drive a resumable product and technical discussion that locks context boundaries, matures a rough idea into requirements and implementation options, and produces one reviewed handoff contract before formal specification.

## Context

- Primary inputs: the user's idea, the current discussion session under `.specify/discussions/<slug>/`, passive project memory, boundary evidence, and project cognition only when the discussion reaches source-grounded technical judgment.
- `discussion-state.md` is the durable session state source of truth.
- `sp-discussion` is upstream of `sp-specify`; it does not create feature branches or write formal feature artifacts.

## Process

- Create or resume the discussion session.
- Run the Context Boundary Gate before project-specific technical options, affected-file claims, implementation-path claims, or handoff generation.
- Ask one boundary or high-impact question at a time.
- Preserve key decisions in `discussion-log.md`.
- Keep `requirements.md`, `technical-options.md`, `project-context.md`, and `open-questions.md` current.
- If the user asks to transfer functionality into another project, lock `target_project_root` immediately before technicalizing.
- When the user explicitly asks to hand off or continue the next stage, write `handoff-assessment.md` first.
- If the direction is coherent and boundary-locked, write exactly one complete handoff package: `handoff-to-specify.md` and `handoff-to-specify.json`.
- If the direction is too broad to express as one coherent package, continue the discussion instead of writing candidate-specific handoff files.
- Run handoff self-review and require user confirmation before marking `handoff-ready`.
- When senior consequence analysis triggers, preserve `CA-###` obligations, affected objects, lifecycle states, dependency impact, recovery/validation needs, coverage gaps, and stop-and-reopen conditions in the unified handoff pair.

## Output Contract

- Maintain the independent discussion state and artifacts under `.specify/discussions/<slug>/`.
- Provide 2-3 project-grounded technical options only after the relevant boundary is locked.
- Report unresolved questions honestly instead of forcing planning readiness.
- Write `handoff-to-specify.md` and `handoff-to-specify.json` together; both files are mandatory for a valid handoff.
- Do not write separate split planning artifacts or candidate-specific handoff files.
- When explicit handoff is requested, include `handoff_goal`, `context_boundary`, `implementation_target`, `source_evidence`, `blocking_unknowns`, `downstream_instructions`, `quality_gate`, and a Must-Preserve Ledger.
- Do not mark handoff ready if role objects, target path context, evidence provenance, self-review status, user confirmation, or blocking unknown handling is missing.
- Preserve `coverage_status`, `planning_gate_status`, `hard_unknown_count`, and `open_conflict_count` for the downstream fidelity gate.

## Guardrails

- Do not edit source code or tests.
- Do not create feature branches or feature directories.
- Do not automatically invoke or route into `sp-specify`.
- Do not make project-specific technical claims before the Context Boundary Gate and staged cognition gate pass.
- Do not use current project cognition to prove another project's implementation facts.
