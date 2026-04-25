## Objective

Run the existing implementation contract through the durable Codex teams runtime when the current batch needs explicit coordinated multi-worker execution.

## Context

- This surface is Codex-only and implementation-phase-only.
- It assumes `tasks.md` is already ready and the work should follow the same shared contract as `sp-implement`.
- The teams runtime is the backend, not a replacement workflow contract.

## Process

- Validate runtime prerequisites, leader workspace state, and extension availability.
- Route the prepared implementation batch through the teams runtime backend.
- Keep the same tracker, packet, join-point, and result-handoff semantics as the canonical implementation workflow.

## Output Contract

- Produce the same implementation lifecycle outcomes as `sp-implement`, plus the expected teams runtime state and visibility artifacts.
- Keep the user-facing narrative framed as coordinated teams execution rather than extension internals.

## Guardrails

- Do not teach internal extension commands as the primary product surface.
- Do not use this command before `tasks.md` is ready.
- Do not weaken the shared `sp-implement` contract just because the runtime backend changed.
