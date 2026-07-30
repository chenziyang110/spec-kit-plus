## Fixed Workflow Artifact Boundary

Read canonical workflow artifacts only with `specify-runtime artifact show`. When the worker packet authorizes an artifact mutation, use the specialized owner named by the artifact registry or packet. Generic `artifact prepare` plus `artifact submit` is valid only when prepare explicitly grants submit for that type; fixed-shape artifacts use scaffold plus targeted patch, and result/evidence artifacts use their namespaces. Never overwrite the canonical path directly. Source and test files in the packet's write scope remain normal repository edits.

# Quick Worker Prompt

Use this template when the quick-task leader dispatches a bounded execution lane for `sp-quick`.

## Controller Requirements

- Provide the smallest safe lane description and its acceptance check.
- Provide `work_item_id`, `depends_on`, prerequisite acceptance evidence, and
  the exact work-item acceptance this lane advances.
- Name the touched files or surfaces.
- State whether the lane is part of a larger join point or is the only active lane.
- When the lane is shaped by a PNG, screenshot, mockup, design export, or other reference image, provide the original visual input as a runtime image item/local_image when supported and as a stable project-relative path when available. Do not provide only a prose summary of the image.
- State the expected fidelity mode (`approximate`, `high`, or `inspiration`) and the image-derived constraints the worker must preserve.
- For UI work, provide the confirmed UI Confirmation exactly as approved, including its source material, boundaries, states, and acceptance evidence. The worker must not redesign the confirmed direction.

## Worker Contract

- Complete one smallest safe lane for the assigned `work_item_id` only.
- Do not begin work when any `depends_on` prerequisite lacks the acceptance
  evidence named in the packet; return the dependency blocker instead.
- Treat work-item acceptance as the lane's outcome boundary. Passing a local
  check that does not advance that acceptance is not completion.
- Keep implementation and verification scoped to that lane.
- Return enough structured detail for the leader to patch `STATUS.md` through `specify-runtime artifact patch`; never edit it yourself.
- If reference images are provided, inspect the original image input before making layout, spacing, color, hierarchy, or asset decisions. If the original image is missing or inaccessible, return a blocker instead of implementing from the leader's text summary alone.
- Treat the confirmed UI Confirmation as an implementation constraint. Preserve original references and their intents; if code or runtime evidence conflicts with the confirmed UI direction, stop and return the conflict rather than silently adapting the design.
- If this lane is a bug fix, do not hide the symptom with a surface-only or symptom-only change when the root cause is still unknown. Return a blocker or a narrower diagnostic split and route the investigation toward `/sp-debug`.
- `STATUS.md` remains leader-owned; the worker must not become the resume authority.
- In plain terms: `STATUS.md` remains leader-owned even when delegated execution succeeds.

## Minimum Return Payload

- Lane goal
- `work_item_id`, `depends_on`, and prerequisite evidence consumed
- Work-item acceptance evidence produced or still missing
- What changed
- Verification run
- Files or surfaces touched
- Reference images viewed, or the blocker explaining why an image could not be inspected
- Recommended next action
- Blocker or concern
- When structured delegated results are available, return a `WorkerTaskResult`-style payload so the leader can merge execution state without reinterpreting prose.
- When the leader provides a runtime result channel, execute the complete runtime-owned argv prefix from the packet, append `--result-json '<inline-json>'`, and submit the normalized envelope (or use the integration's runtime-managed team channel). The Quick command also needs its runtime-supplied workspace and lane ID, so never reconstruct an incomplete command or create/overwrite a result file.
- The worker must not enter `idle` before the required inline handoff is submitted or returned.
- If the handoff channel fails, return that failure explicitly instead of idling silently.

## Guardrails

- Do not widen the assigned work item or lane beyond its confirmed quick-task outcome.
- Do not rewrite adjacent surfaces without explicit instruction.
- Do not use a surface-only or symptom-only patch as a substitute for root-cause work on a bug fix.
- If the lane is too large, stop and return a narrower proposed split.

## Inline Project Cognition Handoff

When you changed project-related files, include `changed_paths`, `behavior_surfaces`, `generated_surfaces`, `state_contracts`, `verification`, `known_unknowns`, and `confidence_notes` in the worker result so the parent workflow can build the inline project cognition update payload. Use `known_unknowns` only for blockers that make the update unsafe to trust; put non-blocking scope notes such as excluded unrelated dirty workspace paths in `confidence_notes`.
