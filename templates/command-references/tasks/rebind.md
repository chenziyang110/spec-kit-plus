Trigger: an existing task package is stale after a verified Test Design refresh or an adopted Plan UI contract.

Purpose: repair the current binding without discarding accepted/deferred task history.

Preserved Contract: the runtime owns all bindings, task projections, packets, handoffs, and the recovery audit; upstream approval and readiness gates remain mandatory.

## Verify the Recovery Inputs

Require `tasks.rebind` through `specify-runtime api ensure --capabilities tasks.rebind --format json` (or inspect `api list` once on an older runtime). If absent, report the missing capability and use the runtime's install/repair route; never replace this operation with direct writes, lifecycle deletion, or an unrelated full rebuild.

Verify the current producer-owned Tasks projection with `test-design projection-verify`. Missing, stale, foreign, tampered, or unpublished Test Design returns to `{{invoke:test-design}}`. Missing or invalid Plan/registered Design returns to its owning workflow. Rebinding must not select a newer approval implicitly or turn a placeholder UI contract into invented design truth.

Read the existing version-2 `task-index.json` and current feature `test-design/handoff-to-tasks.json` through targeted `artifact show`; take each exact `data.sha256`. Read the existing workflow through `workflow show` and take its current revision; it must be in `tasks` or `implement`. Use revision `0` only when `workflow.json` is absent. Other stages return to the owning workflow's guarded reopen route. Confirm that any started unresolved task reaches its owning safe recovery boundary first. Accepted/deferred tasks, lifecycle records, result bytes, and stable task IDs are preserved.

## Apply One Guarded Rebind

```text
specify-runtime tasks rebind --feature-dir <feature-dir> --expected-task-index-sha256 <current-index-sha256> --expected-workflow-revision <current-revision> --expected-test-design-handoff-sha256 <verified-handoff-sha256> --reason <repair-reason> --format json
```

If the current handoff's case/data membership changed, add `--task-updates-json` with one object keyed by existing unstarted `pending`/`ready` task IDs. Each value may contain only `test_case_refs`, `test_data_refs`, and `ui_contract`. Obtain the exact payload shape through `api schema tasks-rebind-updates-input`; pass small JSON inline and large JSON through stdin `-`, including on Windows. `@path` may refer to existing project-contained input; do not create a temporary authoring file merely to transport JSON.

Keep every task's refs within the verified handoff and their unions all-and-only its case/data arrays. Pending UI updates retain the exact adopted Plan/registered Design identity, immutable digests, and task-local subsets; the complete pending task graph still has to satisfy its required coverage. Runtime-owned binding/status/version fields cannot be supplied. If an accepted/deferred task's preserved contract conflicts with the new truth, stop at the returned owning repair boundary instead of rewriting its history.

The runtime compare-and-swap transaction refreshes the canonical index, rendered Markdown, downstream handoffs, and existing affected pending packets together, and records an immutable `task-rebind-history` audit. Stale guards, unresolved started work, invalid references, and missing approved design remain blockers. On guard drift, reread and reassess the current inputs before another attempt; do not blindly substitute new hashes.

## Resume Readiness Validation

Retain the returned `history_ref`/`history_sha256` and transaction receipt. Confirm the refreshed task-index and handoff digests, preserved task IDs, and refreshed UI task IDs from the response. Rebinding does not advance workflow state or create new implementation, Review, or human acceptance evidence. Resume the existing Tasks validation/finalize/handoff path and `workflow complete-stage`; stale task artifacts or handoffs must still block completion.
