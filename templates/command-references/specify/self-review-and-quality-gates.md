Trigger: before reporting a specification package as planning-ready.

Purpose: preserve artifact self-review, planning-readiness checks, and concise quick guidelines.

Preserved Contract: written artifacts must pass self-review before user review and planning handoff.

## Artifact Self-Review

Before reporting completion, review the written artifacts, not just the chat summary. Review the written `spec.md`, `alignment.md`, and `context.md` as the minimum artifact set.

- No placeholders, TODOs, stale markers, or unresolved clarification markers remain unless the package is explicitly not planning-ready.
- If high-risk artifact review triggers, a read-only reviewer lane MUST run before handoff. If no high-risk review trigger is present, a reviewer lane MUST NOT be added. Review routing is condition-triggered, not preference-triggered.
- Requirements are testable and unambiguous.
- `spec.md`, `alignment.md`, `context.md`, `workflow-state.md`, and the compatibility handoff do not contradict each other.
- Every discussion-originated capability-like upstream signal has a disposition row.
- Every deferred or dropped upstream signal has a source, reason, user confirmation status, and reopen trigger.
- Every out-of-scope conflict with upstream wording is recorded in `Out-Of-Scope Conflicts`.
- Acceptance proof matches the confirmed scope.
- UI/API wording in the spec does not imply deferred capabilities are already real.
- If the self-review finds planning-critical gaps, update the artifacts and repeat the review before closeout.

## Quick Guidelines

- Focus on what users need, why they need it, and what a planner must preserve.
- Start with whole-feature understanding before capability details.
- Keep one high-impact question at a time.
- Compare two or three approaches before locking the spec shape.
- Make semantic term narrowing explicit and source-linked.
- Read discussion source files when a discussion handoff exists; the handoff summary is not enough.
- Distinguish confirmed facts, low-risk assumptions, unresolved questions, deferred scope, and dropped scope.
- Avoid implementation design except where a dependency, constraint, boundary, or planning risk must be named.
- Keep generated artifacts concise, reviewable, and useful to `/sp.plan`.
- Do not treat product minimization as the default strategy. Scope reduction requires user confirmation before it can shape `spec.md`.
- Before dispatching independent review or evidence work, use `choose_evidence_lane_dispatch(command_name="specify", snapshot, workload_shape)` and record `lane_mode: read-only-evidence`, `dispatch_shape: one-subagent | parallel-subagents`, and `execution_surface: native-subagents` when a validated isolated read-only lane exists. Use delegated read-only lanes only for isolated review/evidence packets, never for source edits or artifact writes. UI reference artifact work uses `choose_ui_reference_lane_dispatch` and the `ui-reference-artifact` lane instead.
- Record impacted surfaces and change-propagation expectations, major affected surfaces, verification entry points and minimum evidence expectations, and known unknowns or stale evidence boundaries that could change planning safety.
- Route to `/sp.clarify` when planning-critical ambiguity remains around scope, workflow behavior, constraints, or success criteria.
- Do not recommend `/sp.plan` until the written artifacts pass self-review and user review has been requested.
