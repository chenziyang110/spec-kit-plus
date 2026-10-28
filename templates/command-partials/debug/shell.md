{{spec-kit-include: ../common/user-input.md}}

{{spec-kit-include: ../common/context-sufficiency-choice.md}}

{{spec-kit-include: ../common/design-intelligence.md}}

## Objective

Drive a resumable debugging workflow that finds the real failure mechanism before any fix is accepted.

## Context

- Primary inputs: the user's report, the active debug-session state, the failing runtime or verification evidence, and the task-local project cognition query bundle with readiness and returned `minimal_live_reads`.
- The debug session file under `.planning/debug/` is the durable state source of truth for this workflow.
- Delegated helpers are evidence collectors, not owners of the overall investigation.
- Debug execution is complexity-based: small focused investigations may stay leader-inline, while broad or independent evidence lanes use one or more subagents.
- First understand the report and gather safe bounded evidence through the existing intake and observer gates. Ask for missing reporter facts only when they block diagnosis. After the failure mechanism and a concrete repair are supported, present one readable Debug Understanding Checkpoint explaining the discovered problem, decisive evidence, proposed fix, affected scope, expected outcome, risks, and validation. Wait for explicit approval before fix/source/test/harness/persistent instrumentation writes or fix-worker dispatch. `understanding_confirmed` is a repair gate, not a diagnosis prerequisite. For applicable UI symptoms, use provisional source-backed observations during diagnosis; keep UI Confirmation independent in state but fold its confirmed target baseline into the same readable `界面方向` section and ask once before repair. Persist both decisions through fresh `specify-runtime artifact patch` leases.
- **UI Debug Mode (Design Intelligence):** when the symptom is visual, interaction, or presentation, classify into at least one issue class before fixing: **visual/layout** (spacing, alignment, overflow, responsive), **UX/interaction** (unclear action, bad feedback, confusing flow; broken or missing pointer/touch, hover, focus, keyboard, loading, empty, populated, partial, error, permission, offline, retry, undo, or recovery), **resize/reflow** (stretch/compression loses focus, selection, scroll, overlays, unsaved input, actions, or reachable overflow), or **taste/generic-look** (template-like, no hierarchy, noise, anti-slop or design-DNA drift). Happy-path-only screens that collapse on state/interaction still count. Reproduce the exact input event, data condition, resize path, and state before and after the fix. Record issue, reason, and design-aware fix direction in the debug session.
- Treat that as the one initial full repair checkpoint. If later evidence materially changes the approved repair, boundary, UI target, risk, or authority, use the delta-only Debug Checkpoint Amendment contract after first explaining why the prior confirmation is no longer sufficient. The same approved repair does not require another confirmation.

## Debug Checkpoint Card

{{spec-kit-include: checkpoint-card.md}}

## Process

- Recover the debug session through `specify-runtime artifact show`, or initialize it through `specify-runtime artifact scaffold --kind debug-session --path .planning/debug/[slug].md`; never read or create it directly.
- Gather evidence through the current investigation strategy.
- For consequence-sensitive failures, trace affected objects, dependency loops, control/observation states, adjacent risk targets, and any `CA-###` stop-and-reopen conditions before accepting a fix.
- Apply a fix only after the failure mechanism is understood well enough to justify it and the user has approved the concrete repair checkpoint.
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

## Professional UI Contract Continuity

For a UI defect, identify the violated exact row/object in `surface_catalog`,
`scenario_matrix`, `interaction_matrix`, `editing_matrix`, `data_state_matrix`,
`accessibility_matrix`, `navigation_matrix`, `content_matrix`,
`motion_contract`, or `usability_validation`; preserve component governance and
never rewrite the
approved contract during diagnosis. Reproduce risk-based scenarios rather than
an unbounded Cartesian product, and do not substitute screenshots for required
target-user review.
