{{spec-kit-include: ../common/user-input.md}}

## Objective

Explain the current stage artifact in plain language so the user can understand what the system believes, what is settled, what remains open, and what the next stage would do.

## Context

- Primary inputs: the most relevant current stage artifact plus any immediately supporting artifacts needed to explain it accurately.
- This command is explanation-only. It does not invent state that is absent and does not rewrite the underlying files.
- If limited collaboration is used for a supporting cross-check, the final explanation still converges back to one render step.

## Process

- Resolve the current stage artifact deterministically.
- Load only the supporting context needed to explain it faithfully.
- Optionally run a bounded cross-check lane when the current artifact genuinely benefits from it.
- Render one final structured explanation in the user's language.

## Output Contract

- Produce a stage-aware explanation with status, risk, and next-step framing.
- Keep the explanation grounded in what is actually on disk.
- Be explicit when implementation status or another expected artifact is absent.

## Guardrails

- Do not invent missing state.
- Do not rewrite stage artifacts from inside `/sp-explain`.
- Default to `single-lane` unless a supporting cross-check lane is justified.
