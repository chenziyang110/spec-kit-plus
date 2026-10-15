## Fixed Workflow Artifact Boundary

Read canonical workflow artifacts only with `specify-runtime artifact show`. When the worker packet authorizes an artifact mutation, use the specialized owner named by the artifact registry or packet. Generic `artifact prepare` plus `artifact submit` is valid only when prepare explicitly grants submit for that type; fixed-shape artifacts use scaffold plus targeted patch, and result/evidence artifacts use their namespaces. Never overwrite the canonical path directly. Source and test files in the packet's write scope remain normal repository edits.

# Quick Worker Prompt

## Output Asset Scope

Create ancillary documents, reports, or media only within the assignment's authorized output scope. Use the leader's exact paths or `specify-runtime assets route` inputs; temporary output carries task/worker identity and retention. Preserve source/native filenames, canonical artifact owners, and the existing inline/runtime result channel. Reading a file does not authorize relocating it. Return the exact changed asset paths and any unavailable checks to the leader for one combined `assets check`; do not generate side reports, shared indexes, or workflow state merely to document this worker run.

Use this template when the quick-task leader dispatches a bounded execution lane for `sp-quick`.

Before confirmation, a read-only evidence worker is an intake lane with named
read paths, safe-check permissions, no product write scope and stop conditions.
Return inspectable current findings and source/check refs; do not call
`quick item-start`, consume an implementation packet, edit product/test/harness
files, add persistent instrumentation or claim Q acceptance. The execution
contract below starts only with the exact runtime-confirmed or validated
inherited proposal and its Q/Work gates.

## Controller Requirements

- Provide the smallest safe lane description and its acceptance check.
- Provide a runtime-compiled packet from
  `specify-runtime quick packet-compile <quick-id> --item Qn`, or the equivalent
  fields: `work_item_id`, `depends_on`, prerequisite acceptance evidence, and
  the exact work-item acceptance this lane advances.
- Name the touched files or surfaces.
- Carry the confirmed current-state evidence, concrete recommended change and risk boundaries alongside the deliverable and acceptance; do not lose the basis of the approved proposal.
- State whether the lane is part of a larger join point or is the only active lane.
- When the lane is shaped by a PNG, screenshot, mockup, design export, or other reference image, provide the original visual input as a runtime image item/local_image when supported and as a stable project-relative path when available. Do not provide only a prose summary of the image.
- State the expected fidelity mode (`approximate`, `high`, or `inspiration`) and the image-derived constraints the worker must preserve.
- For UI work, provide the confirmed UI Confirmation exactly as approved, including its source material, boundaries, states, and acceptance evidence. The worker must not redesign the confirmed direction.
- When reconstruction, migration, adaptation, or completion is source-grounded,
  provide the confirmed `source_continuity` subset and the original accessible
  screenshot/HTML/live/source/runtime/business authority refs. Include exact
  surface and action bindings, `business_outcome` / `final_state`,
  `asset_bindings`, and any `unresolved_gaps`. The declared coverage surface,
  interaction, and component ID sets must exactly match the supplied binding
  targets and task UI contract; report a blocker rather than silently skipping
  an ID. Do not hand the worker a prose summary in place of inspectable evidence.

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
- For a source-continuity lane, implement only its assigned source-target
  bindings. Preserve the confirmed `preserve`/`adapt`/`replace`/`merge`/`split`/
  `retire` disposition; do not silently omit a deep surface or retire an
  unexplored one. Implement each assigned `action_bindings` row's exact
  `interaction_id`, `source_refs`, `user_promise`, `business_outcome`,
  `side_effects`, `final_state`, and `verification`; exercise linked
  interaction/scenario feedback and recovery. A clickable shell or present
  handler is not completion.
- Implement exact `asset_bindings` fields: `component_id`, `semantic_role`,
  `source_refs`, `target_strategy`, `target_ref`, `provenance`, `fallback`, and
  placeholder policy. Obey
  `placeholder_policy: forbid-character-substitution`: never use Unicode,
  emoji, ASCII, or arbitrary text glyphs as substitutes for missing icons or
  images. Return a blocker or owned replacement request instead.
- If runtime/source inspection discovers a missing surface, action, outcome,
  state, asset, or evidence conflict, return it as `unresolved_gaps` and stop
  the affected claim rather than guessing beyond the confirmed packet.
- Preserve bound `component_states`, `state_variants`, and `native_operation`
  details through Lab observations: disabled behavior and each label/indicator
  visual state are separate checks; every source image state retains its exact
  mapping/dimensions; native actions require API/permission evidence and an
  observed before/after system effect. Follow the adapter's additional state
  and asset-variant binding targets; aggregate PASS cannot replace them.
- Before returning success for a source-continuity Q item, run
  `specify-runtime evidence source-continuity-manifest --quick-id <quick-id>
  --item-id Qn`, inspect the live tool inventory, and call
  `source-continuity-adapter-bridge`. It maps signals through
  `source-continuity-adapter-catalog`; `source-continuity-adapter-probe` and
  `source-continuity-adapter-plan` remain lower-level fallbacks. Compile
  `source-continuity-adapter-execution` from the exact Plan and execute only its
  packet actions, targets, evidence, permissions, preconditions, and stop
  conditions. Register captures with
  provenance `adapter:<adapter_id>`, bind evidence rows and the observation to
  the returned plan, and submit them with `specify-runtime evidence
  source-continuity-validate --quick-id <quick-id> --item-id Qn --manifest
  <manifest-ref> --adapter-plan <adapter-plan-ref> --adapter-execution
  <adapter-execution-ref> --input-json
  '<observed-result-json>'`. Include the returned exact coverage,
  `source_continuity_adapter_plan_ref`/SHA-256 and
  `source_continuity_adapter_execution_ref`/SHA-256 and
  `source_continuity_lab_report_ref`/SHA-256 under `ui_verification`;
  `item-accept` rejects stale, incomplete, or handwritten proof.
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
- Source-continuity authority refs inspected; surface/action/asset bindings
  completed; source-target real-entrypoint scenarios run; observed
  `business_outcome` and `final_state`; and remaining `unresolved_gaps`
- Recommended next action
- Blocker or concern
- When structured delegated results are available, return a `WorkerTaskResult`-style payload so the leader can merge execution state without reinterpreting prose.
- When the leader provides a runtime result channel, execute the complete runtime-owned argv prefix from the packet, append `--result-json <inline-json|@path|->`, and submit the normalized envelope (or use the integration's runtime-managed team channel). Keep small payloads inline, send large model-authored JSON through stdin, and use `@path` only for an existing runtime-owned or registered project artifact. The Quick command also needs its runtime-supplied workspace and lane ID, so never reconstruct an incomplete command or create/overwrite a result file.
- The worker must not enter `idle` before the required structured handoff is submitted or returned.
- If the handoff channel fails, return that failure explicitly instead of idling silently.

## Guardrails

- Do not widen the assigned work item or lane beyond its confirmed quick-task outcome.
- Do not rewrite adjacent surfaces without explicit instruction.
- Do not use a surface-only or symptom-only patch as a substitute for root-cause work on a bug fix.
- If the lane is too large, stop and return a narrower proposed split.

## Inline Project Cognition Handoff

Before source-changing work, require `specify-runtime api ensure --capabilities cognition.worker-delta.v1 --format json` through the project-pinned runtime. A missing capability returns a blocked handoff for runtime repair or upgrade before edits/submission.

Return `cognition_delta` in the existing WorkerTaskResult: `schema: "spec-kit-cognition-delta-v1"`, `version: 1`, and the packet's identity. Report all retained `changed_paths`, including edits from failed or blocked attempts; describe added/modified/deleted/renamed paths in `path_changes` (a rename includes both `old_path` and `new_path` in the path denominator). Preserve relevant `behavior_surfaces`, `owner_surfaces`, `consumer_surfaces`, `interfaces`, `generated_surfaces`, `generated_surface_notes`, `state_contracts`, `evidence_refs`, `verification_evidence`, `invalidated_claim_refs`, `known_unknowns`, `confidence_notes`, and `recovery` as JSON arrays/objects, including nested evidence. These are worker candidates; the runtime owns submission history, source binding, acceptance, and global cognition. Return through the existing result channel; do not write those owners or invent an accepted binding. Legacy path/semantic aliases remain readable, but conflicting values are refused. Use `known_unknowns` only for blockers that make the update unsafe to trust; put non-blocking scope notes such as excluded unrelated dirty workspace paths in `confidence_notes`.

## Exact Task Scope Availability

After the owning runtime compiles the canonical current task packet, and before
dependent graph consumption, require `specify-runtime api ensure --capabilities
cognition.scope-availability.v2 --format json`, then run `specify-runtime cognition
check --task-packet <exact-project-relative-packet-path> --format json`. Use the
compiler's returned packet path; do not assemble a substitute packet or infer
complete read dependencies from prose. Quick confirmation items declare optional
`read_scope` as an explicit array of exact paths, including required UI contract
and original reference inputs when applicable. Missing legacy `read_scope` is
unknown; explicit `[]` is a complete empty declaration. Null, non-arrays and
non-string paths refuse. Read metadata follows execution `write_scope` digest
exclusion; it never changes registered UI approval or grants worker write scope.

Carry native `availability`, `scope_ready`, `global_status`, `debt_assessments`,
`reasons`, `minimal_live_reads` and `binding` separately. Only an actual version 2
ready result permits scoped advisory graph navigation; proven unrelated debt
remains visible globally. Blocked/degraded/unavailable or unknown proof suspends
dependent graph consumption and uses bounded current live reads, with gaps
explicit. Do not erase blocked results or treat advisory warnings as uniform
protection. Commands without a canonical packet keep the global check and cannot
assert unrelated debt. This route applies with hooks and without hooks on every
CLI and both profiles.

At handoff/resume and before reusing graph context, rerun the same native check
with `--availability-json <previous-native-binding-json>` against the current
canonical packet. Changed source/packet/status/dependency/claim bytes or an old
contract invalidate reuse; repair the owning proof and obtain a new result. Scope
readiness never declares the project globally fresh, grants source write
authority, sets workflow `claim_ready`, or replaces independent Review and human
Accept. Preserve normal packet/Work/UI prerequisite and approval gates.
