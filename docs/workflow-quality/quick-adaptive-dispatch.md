# Quick executor selection

The runtime adds an opt-in `--leader-direct` flag to `quick item-start`. Its
legacy default remains a delegated worker. This is distinct from both the
no-workspace context-direct intake branch and the audited spawn-failure
`leader-inline` fallback. No new workflow stage or confirmation bypass exists.

Discover support through `api show quick.item-start` or its existing `api pack`
entry: inspect `execution_contract.schema == quick-item-dispatch-v1`, not only
capability IDs. Help exposes the same contract under `execution_contracts`.
Unknown/absent contracts use the old worker path. A recorded direct task requires
a compatible pinned runtime on resume; do not downgrade, relabel its state or
start a replacement writer when that runtime is missing.

```sh
specify-runtime api show quick.item-start --format json
specify-runtime quick item-start <id> --item Q1 --leader-direct --format json
```

The confirmed checkpoint, existing Work identity/fence and execution guard are
still required. Start returns the compiled packet and work_claim: there is no
need for a duplicate packet-compile immediately before or after it. Verify both
the response and packet report leader-direct and requires_worker=false. False
alone does not authorize writes. Do not edit another active worker's scope.

Choose the executor before the item's first start. A resumed direct item keeps
its mode without a flag. An active/blocked legacy worker cannot be converted
in place. If context/risk changes, pause and reconcile scope/authority rather
than changing executors or weakening the original acceptance contract.

Both normal modes use the existing stage-owned `result submit --command quick`
channel, retaining its historical worker-results directory and result-binding
field names. Direct acceptance checks the existing status, scope, lane identity,
reuse and applicable source-continuity proof. It additionally requires normalized
non-empty validation_results with every command reported passed and no blockers.
`allow-inline`, including item-accept's one-shot form, cannot waive direct proof.
Direct reaccept/close also rechecks the result and stored lane/path binding.
Reported validation is not independent proof of execution; the Leader still
runs the actual checks, performs required review, and completes existing
cognition and Git-delta/audited execution closeout. No permission or mandatory
review is granted by an execution-mode label or JSON Schema validation.

Advanced SPX Quick selects direct for a bounded low-risk item only when context,
ownership, consumers and checks are understood and independent implementation
is not required. Complex, high-risk, uncertain or isolation-sensitive work uses
workers; independent review remains independent. The existing task contract is
updated alongside the Skill. Classic's explicit delegated defaults and passive
bundle are not changed to optimize Advanced; the shared runtime remains
compatible when the flag is omitted. Generated installations are not changed by
committing these source templates, and no binary is released by this change.

## Verification boundary

The new helper tests cover selection/resume, flag-shaped values, no fallback
substitution, validation and contract preservation. Existing compact/helper
tests and the complete shipped JSON Schema are also exercised locally. Source
prompt assertions check policy anchors, not model behavior or installed output.
`quick_execution_direct_integration_test.go` uses the existing real Work/Quick
fixtures to cover start/resume, structured proof, stale fence, failed checks,
out-of-scope results, active-worker protection, and reaccept/close. Execute it
in a complete checkout before rollout:

```sh
cd tools/specify-runtime
go test -count=1 -run 'TestQuick(Direct|Output|Scope|Queue|Lazy|Compact|Resume)' .
go test -count=1 ./...
go vet ./...
```

Complete runtime/profile/install tests, real-host agent A/B and passing cloud CI
remain rollout gates, not consequences of a standalone helper pass. No production
token, cost, latency or quality-retention improvement is quantified here.
