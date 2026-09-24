# Recover a stale task binding

Use this route when current verified Test Design or an adopted Plan UI contract
must refresh an existing graph. Keep accepted/deferred task IDs and all
lifecycle/result evidence; deleting the graph, rebuilding accepted work, or
patching CLI-owned bindings is never the recovery operation.

1. Require `tasks.rebind` with `api ensure --capabilities tasks.rebind --format json`;
   use `api list` once when the old runtime lacks `ensure`. A missing capability
   needs runtime repair/upgrade. Do not improvise a filesystem fallback.
2. Verify the producer-owned Tasks projection with `test-design projection-verify`.
   Stale, missing, tampered, foreign, or unpublished inputs return to
   `$spx-test-design`; invalid Plan or Design returns to its own producer. Use
   the exact adopted registered design, never the latest unrelated approval.
3. Through `artifact show`, read the current index and feature
   `test-design/handoff-to-tasks.json`, retaining each `data.sha256`. Read
   `workflow show` for its current revision and require `tasks` or `implement`;
   other stages use the owning workflow's guarded reopen. `0` is valid only
   when `workflow.json` is absent. The existing graph must be version 2.
   Resolve started unresolved work through its owner
   before rebinding. Accepted/deferred records remain untouched.
4. Invoke one guarded operation:

   ```text
   specify-runtime tasks rebind --feature-dir <feature-dir> --expected-task-index-sha256 <current-index-sha256> --expected-workflow-revision <current-revision> --expected-test-design-handoff-sha256 <verified-handoff-sha256> --reason <repair-reason> --format json
   ```

   Supply optional `--task-updates-json` only when needed, following
   `api schema tasks-rebind-updates-input`. Key by existing unstarted
   `pending`/`ready` task ID; values allow only `test_case_refs`,
   `test_data_refs`, and `ui_contract`. Pass semantic JSON inline or through
   stdin `-` for large/Windows input; `@path` accepts existing contained input,
   not a reason to create an authoring transport file. Ref unions must consume
   all-and-only the verified handoff. Pending UI uses exact Plan/registered
   Design contracts and required coverage. A change conflicting with preserved
   accepted/deferred contracts stays blocked for its owner.
5. The compare-and-swap transaction refreshes index, Markdown, downstream
   handoffs, and existing affected pending packets together, and persists an
   immutable `task-rebind-history` audit. Retain `history_ref`,
   `history_sha256`, the transaction receipt, refreshed digests, and preserved
   task IDs. On stale guards, re-read and reassess; do not retry with blind hash
   substitution. Rebind neither changes workflow state nor grants new evidence.
6. Resume the existing Tasks validation/finalize/handoff and
   `workflow complete-stage` gates. Stale task artifacts or handoffs still
   block completion; successful rebind alone is not implementation, Review, or
   human acceptance.
