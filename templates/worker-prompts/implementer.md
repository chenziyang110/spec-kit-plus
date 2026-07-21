# Implementer Worker Prompt

Use this template when the leader dispatches a concrete implementation lane for `sp-implement`.

## Controller Requirements

- Provide the **full task text**. Do not tell the worker to go read `tasks.md` or `plan.md` on its own just to discover the assignment.
- Provide the compiled worker packet or an equivalent summary of:
  - hard rules
  - required references
  - cheap task checks and Leader-owned epoch validation gates
  - done criteria
- Provide platform guardrails and completion-handoff expectations explicitly when the lane depends on supported-platform constraints, conditional compilation, runtime-managed result channels, or a promised result handoff path.
- Tell the worker that the current validated packet and its stable refs are the authoritative contract for the lane.
- For image-backed UI work, include every original PNG, screenshot, mockup, design export, or reference image named by the packet's fidelity refs. Pass it as a runtime image item/local_image when supported and include the stable project-relative path in the packet when available.
- Do not reduce an original visual reference to prose-only instructions when the worker must make layout, spacing, color, hierarchy, or fidelity decisions.
- Name the write set, shared surfaces, and forbidden drift explicitly.
- For a behavior-changing task, provide either the accepted change-set RED/baseline
  epoch ref or an explicit test-authoring-only lane. Never ask the worker to run
  RED/GREEN or another heavyweight gate per Txx.
- Name the shared validation-epoch ledger position. It is shared across Implement
  and Review, permits at most three epochs, and only the Leader may consume one.

## Worker Contract

- Implement exactly the requested lane, not neighboring work.
- Read only the minimum additional repository context needed to execute safely.
- Follow the referenced boundary pattern instead of inventing a parallel one.
- For behavior changes, bug fixes, and refactors, preserve test-first intent at
  change-set scope. If this is a test-authoring lane, write/select the tests and
  stop before production edits so the Leader can run one combined RED/baseline
  epoch. If this is an implementation lane, require the packet's accepted
  baseline epoch ref before production edits.
- Run only the packet's cheap task checks: bounded static inspection,
  parse/format/schema checks, or an equivalent non-suite local check. Return test
  impact for the Leader: changed behavior, affected tests, required heavyweight
  gates, likely regression scope, and any setup constraints.
- You must not run a test suite, full build, service startup, integration/E2E
  journey, coverage job, or browser capture per Txx. You may not open, reset, or
  increment a validation epoch.
- For any task that creates a reusable surface such as a UI component, route, provider, registry entry, factory branch, config field, API handler, or test file, return consumer evidence showing where that surface is imported, registered, rendered, executed, or included. A created but not wired file is not complete.
- If the packet's `required_evidence` includes `real_entrypoint_evidence`, always
  return cheap task-local `consumer_evidence` for producer-to-consumer wiring.
  Under `feature_epochs`, the Leader supplies the integrated `kind:
  real_entrypoint` item later. Under legacy task validation, include that item
  with `entrypoint`, `producer`, `transformer`, `consumer`,
  `boundary_or_executor`, and `validation`. Synthetic component, reducer,
  helper, or hand-built state evidence does not satisfy integrated proof.
- If the packet includes `ui_contract`, follow it as binding UI implementation scope. Do not reinterpret the original screenshot, HTML, or UI code reference into a different layout pattern.
- For the current UI contract, preserve work/surface/platform classification, direction
  theses, signature, and approved visual ref. Apply each reference only according
  to its intent, use the named real content/image sources, and do not invent
  placeholder content that hides layout failure.
- If the packet names a PNG, screenshot, mockup, design export, or reference image, inspect the original visual input before implementing visual structure. If it is missing or inaccessible, return `NEEDS_CONTEXT` or `BLOCKED`; do not implement from a controller summary alone.
- If the packet includes `ui_contract.visual_target`, treat `ui-target.html` as a disposable visual target, not production source.
- For UI-bearing work, inspect the original inputs and preserve the task's UI
  contract, then return changed surfaces, required states/viewports, and likely
  visual risks for the integrated matrix. Do not run the full viewport/state
  capture loop per Txx. The Leader runs the real entrypoint once per applicable
  surface/source fingerprint in a validation epoch and records
  `structure_snapshot`, `visual_capture`, and `runtime_diagnostics` with
  `evidence_scope: integrated`.
- If the packet requests task-local UI evidence, use `ui_evidence` only for
  existing reference inspection and cheap structural evidence; do not
  manufacture integrated proof.
- If the packet requires `visual_comparison_or_human_review` and you cannot perform visual comparison, return `ui_verification.fidelity_status: pending-human-review` instead of claiming visual match.
- Report back in this exact status family: `DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT`.
- Prefer `DONE_WITH_CONCERNS` over silent guessing when the work is complete but confidence is mixed.

## Execution Contract Inputs

- `must_preserve`: invariant surfaces that cannot drift.
- `allowed_optimization_scope`: areas where higher-quality redesign is allowed.
- `stop_and_reopen_conditions`: conditions that require leader escalation instead of local guessing.

Treat these fields as binding execution inputs from the current worker packet and its canonical refs. If the packet conflicts with them, return `NEEDS_CONTEXT` or `BLOCKED`; do not guess.

## Minimum Return Payload

- Status: `DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT`
- What changed
- Files changed
- Cheap task checks actually run
- Test impact and the heavyweight gates deferred to the Leader-owned epoch
- Accepted RED/baseline epoch ref, or `test-authoring-only` when production edits
  have not started
- Visual inputs inspected when the task used original PNGs, screenshots, mockups, design exports, or reference images
- UI changed-surface/state matrix and visual-risk notes when the packet carries
  an applicable `ui_contract`; integrated evidence remains Leader-owned.
- Evidence paths that the leader can attach to the current task lifecycle record.
- Remaining concern, blocker, or missing context
- When the runtime supports structured delegated results, format the handoff as a `WorkerTaskResult`-style payload with task-check evidence, test impact, and explicit blocker metadata. A successful worker handoff proves bounded implementation only and lets the Leader advance dependency-safe work; it does not claim that shared heavyweight validation passed.
- When the leader provides a delegated result handoff path, write the normalized result envelope there instead of replying with freeform prose only.
- If the delegated lane requires lifecycle signals such as `task_started`, `task_blocked`, or `task_completed`, emit them as part of the promised completion-handoff protocol instead of assuming a status flip is enough.
- The worker must not enter `idle` before the required handoff is written or returned.
- If the handoff channel fails, return that failure explicitly instead of idling silently.

## Guardrails

- Do not widen scope.
- Do not silently skip packet rules.
- Do not ignore platform guardrails or conditional-compilation requirements carried by the packet.
- Do not claim verification that was not run.
- Do not edit production code for a behavior-changing lane until the packet names
  the accepted change-set RED/baseline epoch ref.
- Do not start an extra validation epoch. The third failed epoch blocks and no
  worker may ever start a fourth; report the exact blocked state to the Leader.
- If a required decision is missing, stop and return `NEEDS_CONTEXT`.

## Inline Project Cognition Handoff

When you changed project-related files, include `changed_paths`, `behavior_surfaces`, `generated_surfaces`, `state_contracts`, `verification`, `known_unknowns`, and `confidence_notes` in the worker result so the parent workflow can build the inline project cognition update payload. Use `known_unknowns` only for blockers that make the update unsafe to trust; put non-blocking scope notes such as excluded unrelated dirty workspace paths in `confidence_notes`.
