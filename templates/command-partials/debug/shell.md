{{spec-kit-include: ../common/user-input.md}}

{{spec-kit-include: ../common/design-intelligence.md}}

## Objective

Drive a resumable debugging workflow that finds the real failure mechanism before any fix is accepted.

## Context

- Primary inputs: the user's report, the active debug-session state, the failing runtime or verification evidence, and the task-local project cognition query bundle with readiness and returned `minimal_live_reads`.
- The debug session file under `.planning/debug/` is the durable state source of truth for this workflow.
- Delegated helpers are evidence collectors, not owners of the overall investigation.
- Debug execution is complexity-based: small focused investigations may stay leader-inline, while broad or independent evidence lanes use one or more subagents.
- Before substantive investigation, present one Debug Understanding Checkpoint covering user-owned problem facts, expected behavior, occurrence conditions, investigation boundary, explicit fix authority, assumptions to correct, and reconfirmation triggers. Technical hypotheses and the evidence sequence belong to the agent. For applicable UI symptoms, append the independent UI Confirmation target baseline and ask for one combined confirmation; persist both decisions through fresh `specify-runtime artifact patch` leases.
- **UI Debug Mode (Design Intelligence):** when the symptom is visual, interaction, or presentation, classify into at least one issue class before fixing: **visual/layout** (spacing, alignment, overflow, responsive), **UX/interaction** (unclear action, bad feedback, confusing flow; broken or missing hover, focus, keyboard, loading, empty, error), or **taste/generic-look** (template-like, no hierarchy, noise, anti-slop or design-DNA drift). Happy-path-only screens that collapse on state/interaction still count. Record issue, reason, and design-aware fix direction in the debug session.
- Treat that as the one initial full checkpoint. If later evidence materially changes the confirmed boundary or authority, use the delta-only Debug Checkpoint Amendment contract after first explaining why the prior confirmation is no longer sufficient.

## Debug Checkpoint Card

{{spec-kit-include: checkpoint-card.md}}

## Process

- Recover the debug session through `specify-runtime artifact show`, or initialize it through `specify-runtime artifact scaffold --kind debug-session --path .planning/debug/[slug].md`; never read or create it directly.
- Gather evidence through the current investigation strategy.
- For consequence-sensitive failures, trace affected objects, dependency loops, control/observation states, adjacent risk targets, and any `CA-###` stop-and-reopen conditions before accepting a fix.
- Apply a fix only after the failure mechanism is understood well enough to justify it.
- Verify the result and persist the session transition through a fresh `specify-runtime artifact patch` lease before any resolution claim.

## Output Contract

- Keep the debug session state, current hypothesis, evidence, and verification outcome explicit.
- Produce a verified fix only when the evidence supports it.
- Report blocked or unresolved states honestly when the investigation cannot yet close.

## Guardrails

- No speculative fixes before evidence supports the failure mechanism.
- No final resolution without fresh verification evidence.
- No subagent may take ownership of the debug session state.
- No subagent-assisted work may continue without a safe lane; blocked debug execution records `subagent-blocked`, `execution_surface: none`, and a concrete blocked reason.
