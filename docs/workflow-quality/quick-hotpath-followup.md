# Quick hot-path follow-up

## Source changes

`runExecution` now passes a lazy pulse renderer to `quickExecutionResponseData`.
The existing compact projection first decides whether its exact decision
binding can replace confirmation context. Only full output or a binding-conflict
fallback constructs the human pulse. Packet-only output never constructs it.
All actions still load their canonical confirmation, perform their existing
checks and mutations, and return their unchanged packet and Work evidence.
This is not lazy validation or a change to authorization.

The new helper is compared against the previous eager presentation for full,
compact and fallback responses. It preserves false/empty/future fields, existing
pulse values and its input map. Successful compact output has the same bytes as
before; the optimization removes unused renderer work rather than claiming an
additional token reduction.

Queue discovery now omits explicitly `blocked` items from `ready_item_ids` and
includes them in `blocked_item_ids` even when their dependencies are satisfied.
Independent ready work remains visible. This changes read-only queue reporting,
not the lifecycle: it does not auto-clear a block, change acceptance, or add a
new unblock gate. The existing explicitly selected `item-start` recovery route
and its Work/confirmation/dependency checks remain unchanged.

## Validation and remaining boundaries

Standalone tests run directly from the repository:

```sh
cd tools/specify-runtime
go test -race -count=1 quick_execution_response.go quick_execution_lazy_test.go
go vet quick_execution_response.go quick_execution_lazy_test.go
go test -run '^$' -bench BenchmarkQuickLazyPulse -benchmem \
  quick_execution_response.go quick_execution_lazy_test.go
```

The benchmark uses a synthetic pulse builder. Its renderer-call and allocation
counts are not model token bills, live end-to-end speedups or quality scores.
Queue regression tests additionally compile against the full runtime:

```sh
go test -count=1 -run 'TestQuick(Queue|Lazy|Compact|Resume)' .
go test -count=1 ./...
```

The local queue check used exact extracted queue functions plus restricted type
fixtures; it reproduced the old ready-list bug and passed with the change. That
is not a full-package pass. Full runtime, installation/profile and live agent
checks remain required before merge or release.

This follow-up does not apply the separate third-increment discovery patch.
`quick --help` / `api show` / `api pack` integration and the argument parser from
that patch remain pending. Rebase that patch against this change before use;
its old strict-baseline installer intentionally refuses a different commit.
No generated prompt, delegation policy, release or public binary is changed.
