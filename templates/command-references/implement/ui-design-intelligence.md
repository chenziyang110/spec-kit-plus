Trigger: before generating UI for UI-bearing work and again before integrated UI validation.

Purpose: load the Design Intelligence UI implementation and evidence contract only for UI-bearing implementation work.

Preserved Contract: UI-bearing implementation must query exact registered
design inputs, preserve anti-slop and interaction fidelity rules, and satisfy
the integrated visual, smoothness, and source-continuity evidence contracts
without reconstructing them from memory.

{{spec-kit-include: ../../command-partials/common/design-intelligence.md}}

## UI Implementation Rules

Query the task's exact registered design change, UI System Model (tokens,
components, states), surface-aware anti-slop policy, and the task
`ui_contract` through `specify-runtime artifact show`. Prefer visual hierarchy
and the component system over generic equal-weight card grids. Execute the
declared pointer/mouse, keyboard/focus, touch, and command paths; verify each
interaction row's event sequence, immediate feedback, focus, repeat,
cancellation, and pending behavior plus component `interaction_modes`,
`data_scenarios`, `editing_matrix`, and resize/stretch/overflow behavior
instead of checking only the populated happy path.

Preserve states and changed surfaces through `specify-runtime implement`, and
capture requirements, but do not run the full viewport/state capture loop per
Txx. Group the matrix by integrated surface and capture typed
`structure_snapshot`, `visual_capture`, and `runtime_diagnostics` evidence
through `specify-runtime evidence register|import` with
`evidence_scope: integrated`. Bind shared refs and the task's structured
`ui_verification` into each task lifecycle only through
`specify-runtime implement result-merge|task-accept`; include the required
evidence, difference inventory, accepted deviations, and exact
`covered_smoothness_acceptance_ids`, plus the objective-comparison or
`pending-human-review` result.

For every passing visual comparison, submit only the observed
entrypoint/revision, typed evidence refs, matrix differences, explicit verdict,
and reviewer through `specify-runtime evidence visual-compare --feature-dir
<feature-dir> --task-id <Txxx> --input-json '<observed-comparison-json>'
--format json`. The runtime derives and atomically writes the registered report
from the task's approved preview/manifest/handoff bindings, exact `DS-*`/`DH-*`
coverage, comparison tolerance, and accepted deviations; use its returned
report ref and byte digest in `ui_verification`. Never read or reconstruct
`visual-comparison-template.json`, and never generically submit or patch the
report.

When `smoothness_acceptance_ids` is non-empty, first call
`specify-runtime evidence smoothness-manifest --feature-dir <feature-dir>
--task-id <Txxx> --format json`; execute its exact real-entrypoint viewport,
interaction, reduced-motion, interruption, and performance matrix with
Playwright or the available browser runner; then submit only observations to
`specify-runtime evidence smoothness-validate --feature-dir <feature-dir>
--task-id <Txxx> --manifest <manifest-ref> --input-json
'<observed-result-json>' --format json`. Merge the returned exact coverage,
`smoothness_lab_report_ref`, and `smoothness_lab_report_sha256` into the
lifecycle. The report augments the existing evidence triad; it is not a new
evidence kind. The runtime must resolve the task surface's exact `entrypoint_id`;
missing, unknown, or ambiguous entrypoint bindings block the lab. Task
acceptance revalidates the canonical manifest, current task-index digest, typed
evidence triad, full scenario set, and performance budgets, so a handwritten
or minimal report cannot pass.

When `ui_contract.source_continuity.applicability` is `required`, call
`specify-runtime evidence source-continuity-manifest --feature-dir
<feature-dir> --task-id <Txxx> --format json`. Inspect the current live tool
inventory and call `specify-runtime evidence
source-continuity-adapter-bridge --feature-dir <feature-dir> --task-id <Txxx>
--manifest <manifest-ref> --input-json '<live-tool-inventory>'`. The Bridge
maps generic signals to the embedded `source-continuity-adapter-catalog` and
atomically owns inventory, Probe, and Plan artifacts.
`source-continuity-adapter-probe` is the lower-level provider-binding fallback;
`source-continuity-adapter-plan` is the explicit last fallback for a verified
tool the catalog cannot express. Next compile
`source-continuity-adapter-execution --manifest <manifest-ref> --adapter-plan
<adapter-plan-ref> --adapter-plan-sha256 <sha256>`. Execute only its
per-adapter packets and obey their actions, binding targets, permissions,
preconditions, evidence requirements, and stop conditions; packets never
authorize command/argv/env/script/install fields. Register each capture with
provenance `adapter:<adapter_id>`, put that `adapter_id` on its evidence row,
bind the returned plan ref/digest and composite adapter in the observation,
then submit only observations through `specify-runtime evidence
source-continuity-validate --feature-dir <feature-dir> --task-id <Txxx>
--manifest <manifest-ref> --adapter-plan <adapter-plan-ref>
--adapter-execution <adapter-execution-ref> --input-json
'<observed-result-json>' --format json`. Merge the returned exact coverage,
`source_continuity_adapter_plan_ref`/SHA-256 and
`source_continuity_adapter_execution_ref`/SHA-256 and
`source_continuity_lab_report_ref`/SHA-256 into `ui_verification`.
Acceptance revalidates the task-index, manifest, report, metrics, evidence,
and character-substitution gate; never handwrite the report or treat the
contract's self-consistency as discovery proof.

Query the packet's must-read immutable handoff through
`specify-runtime artifact show` before UI work and resolve selected rows and
implementation bindings from it; a missing file, digest mismatch, unknown ID,
or copied-row mismatch blocks implementation rather than authorizing
reconstruction. This is evidence reuse, not permission to recapture or rerun
the matrix per task. Unavailable objective comparison remains
`pending-human-review`, never an implicit pass. Route an invalid, bootstrap, or
missing design source to `sp-design` instead of inventing one.
