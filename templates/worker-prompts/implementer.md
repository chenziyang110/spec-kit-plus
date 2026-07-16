# Implementer Worker Prompt

Use this template when the leader dispatches a concrete implementation lane for `sp-implement`.

## Controller Requirements

- Provide the **full task text**. Do not tell the worker to go read `tasks.md` or `plan.md` on its own just to discover the assignment.
- Provide the compiled worker packet or an equivalent summary of:
  - hard rules
  - required references
  - verification gates
  - done criteria
- Provide platform guardrails and completion-handoff expectations explicitly when the lane depends on supported-platform constraints, conditional compilation, runtime-managed result channels, or a promised result handoff path.
- Tell the worker that the current validated packet and its stable refs are the authoritative contract for the lane.
- For image-backed UI work, include every original PNG, screenshot, mockup, design export, or reference image named by the packet's fidelity refs. Pass it as a runtime image item/local_image when supported and include the stable project-relative path in the packet when available.
- Do not reduce an original visual reference to prose-only instructions when the worker must make layout, spacing, color, hierarchy, or fidelity decisions.
- Name the write set, shared surfaces, and forbidden drift explicitly.
- For every behavior-changing task, bug fix, or refactor, tell the worker to write the failing test first, capture the RED state, and return the GREEN rerun evidence for the same gate after the fix.

## Worker Contract

- Implement exactly the requested lane, not neighboring work.
- Read only the minimum additional repository context needed to execute safely.
- Follow the referenced boundary pattern instead of inventing a parallel one.
- For behavior changes, bug fixes, and refactors, follow RED -> GREEN -> REFACTOR:
  - write the failing test first
  - verify the RED state before editing production code
  - rerun the same gate and capture the GREEN state before reporting success
- For any task that creates a reusable surface such as a UI component, route, provider, registry entry, factory branch, config field, API handler, or test file, return consumer evidence showing where that surface is imported, registered, rendered, executed, or included. A created but not wired file is not complete.
- If the packet's `required_evidence` includes `real_entrypoint_evidence`, include a `consumer_evidence` item with `kind: real_entrypoint`, `entrypoint`, `producer`, `transformer`, `consumer`, `boundary_or_executor`, and `validation`. Synthetic component, reducer, helper, or hand-built state evidence may be included as support, but it does not satisfy the real-entrypoint requirement by itself.
- If the packet includes `ui_contract`, follow it as binding UI implementation scope. Do not reinterpret the original screenshot, HTML, or UI code reference into a different layout pattern.
- For the current UI contract, preserve work/surface/platform classification, direction
  theses, signature, and approved visual ref. Apply each reference only according
  to its intent, use the named real content/image sources, and do not invent
  placeholder content that hides layout failure.
- If the packet names a PNG, screenshot, mockup, design export, or reference image, inspect the original visual input before implementing visual structure. If it is missing or inaccessible, return `NEEDS_CONTEXT` or `BLOCKED`; do not implement from a controller summary alone.
- If the packet includes `ui_contract.visual_target`, treat `ui-target.html` as a disposable visual target, not production source.
- For UI-bearing work, run the real entry point and iterate: capture every
  required representative viewport/state, inspect the rendered result against
  the original design inputs and `ui_contract`, fix concrete drift, then
  recapture. Passing code tests is not visual acceptance.
- If the packet requires UI evidence, return typed `ui_evidence` entries with
  `kind` and `ref`. Use exactly `structure_snapshot`, `visual_capture`, and
  `runtime_diagnostics`; record platform-specific capture details as metadata,
  not alternative kind names.
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
- Verification run
- RED state evidence when the lane changed behavior
- GREEN state evidence for the same gate after the fix
- Visual inputs inspected when the task used original PNGs, screenshots, mockups, design exports, or reference images
- Typed UI evidence when the packet carries an applicable `ui_contract`.
- Evidence paths that the leader can attach to the current task lifecycle record.
- Remaining concern, blocker, or missing context
- When the runtime supports structured delegated results, format the handoff as a `WorkerTaskResult`-style payload with validation evidence and explicit blocker metadata.
- When the leader provides a delegated result handoff path, write the normalized result envelope there instead of replying with freeform prose only.
- If the delegated lane requires lifecycle signals such as `task_started`, `task_blocked`, or `task_completed`, emit them as part of the promised completion-handoff protocol instead of assuming a status flip is enough.
- The worker must not enter `idle` before the required handoff is written or returned.
- If the handoff channel fails, return that failure explicitly instead of idling silently.

## Guardrails

- Do not widen scope.
- Do not silently skip packet rules.
- Do not ignore platform guardrails or conditional-compilation requirements carried by the packet.
- Do not claim verification that was not run.
- Do not edit production code until the RED state is verified.
- Do not report success without explicit GREEN state evidence for the same gate you used during RED.
- If a required decision is missing, stop and return `NEEDS_CONTEXT`.

## Inline Project Cognition Handoff

When you changed project-related files, include `changed_paths`, `behavior_surfaces`, `generated_surfaces`, `state_contracts`, `verification`, `known_unknowns`, and `confidence_notes` in the worker result so the parent workflow can build the inline project cognition update payload. Use `known_unknowns` only for blockers that make the update unsafe to trust; put non-blocking scope notes such as excluded unrelated dirty workspace paths in `confidence_notes`.
