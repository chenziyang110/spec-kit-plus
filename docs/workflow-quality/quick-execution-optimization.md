# Quick execution: compact responses and truthful resume

## Scope and status

This incremental source change preserves the Quick checkpoint, worker-result,
write-scope, Work/fence, dependency, source-continuity, and closeout gates. It
neither changes delegation policy nor releases a runtime binary. Classic and
Advanced keep their existing default responses and generated instructions.

This remains an opt-in source experiment. Projection helper tests, race checks,
fuzzing and the synthetic serialization benchmark were run locally; the full
runtime package, installed consumer integration and real-agent A/B evaluation
remain unverified. `quick --help` and `api show` do not yet advertise `--compact`.
Before consumer rollout, wire and test those discovery surfaces, verify both
workflow profiles and follow release/installer compatibility checks. Do not
infer runtime support from this document or silently switch generated prompts.

## Optional compact execution output

In a binary built from this change, `item-start`, `allow-inline`, `item-accept`,
and `item-status` accept boolean `--compact`. Without it, output is unchanged.
`packet-compile` stays full: it has no duplicate confirmation/pulse pair.
No stored artifact is compacted.

```sh
specify-runtime quick item-status <id> --compact --format json
```

The opt-in data projection reports `response_schema: quick-execution-compact-v1`.
It removes only `confirmation` and `pulse`, replacing them with the exact
`confirmation_ref`, `confirmation_state`, and `confirmation_digest`. The digest
is the existing decision binding, **not** a hash of the whole confirmation file.
A missing/blank replacement binding, null confirmation, or an existing conflicting
replacement field preserves the full response. Presentation never silently
replaces a future contract field; exact matching fields remain compatible.

All other fields are retained, including the current packet, packet path,
Work claim, worker requirement/proof, inline reason, complete scheduling sets,
blockers and next action. False and empty values are not silently removed.
Errors retain their existing complete diagnostics. Compact output is intended
for a hot execution loop after intake, not as a substitute for reading the
confirmed scope, original inputs, task packet or applicable UI contracts.

For a full read-only context refresh, run the existing command without the flag:

```sh
specify-runtime quick item-status <id> --format json
```

Do not retry a mutation merely to obtain a larger response. Generated prompts
are deliberately unchanged until runtime discovery and end-to-end verification
are complete.

## Resume failure handling

Resuming an in-progress item must persist confirmation before updating the
STATUS projection. Both failures are reported with their persistence phase
and underlying error. A failed resume returns no successful dispatch receipt.
The existing Work claim and in-progress task are retained: repair the I/O
failure, then retry with the same guarded Work identity. This deliberately does
not release ownership over a potentially dirty workspace or claim that the two
files are a single atomic transaction.

## Reproducible validation

The pure projection helpers use only the Go standard library:

```sh
cd tools/specify-runtime
go test -race -count=1 -v quick_execution_response.go \
  quick_execution_response_test.go quick_execution_projection_safety_test.go
go vet quick_execution_response.go \
  quick_execution_response_test.go quick_execution_projection_safety_test.go
go test -run '^$' -fuzz '^FuzzQuickCompactRetainsNonduplicateFields$' \
  -fuzztime=5s -parallel=2 quick_execution_response.go \
  quick_execution_projection_safety_test.go
go test -run '^$' -bench BenchmarkQuickExecutionResponse -benchmem \
  quick_execution_response.go quick_execution_response_test.go
```

The persistence helper tests remain independently runnable:

```sh
go test -race -count=1 quick_execution_resume.go quick_execution_resume_test.go
```

Full-package tests additionally exercise the real Quick CLI, unchanged
worker-result gate, legacy output, injected STATUS projection failure and retry
under the same Work identity. They have not been run successfully here:

```sh
go test -count=1 -run 'TestQuick(Compact|Resume)' .
go test -count=1 ./...
```

The response-size experiment is synthetic and measures serialized **data bytes**,
not complete envelopes, live agent usage, cache behavior, end-to-end latency,
quality retention or API cost. Full state is still constructed before projection,
and complete scheduling lists still scale with task count. For separately
exported per-call accounting, see [Execution usage accounting](execution-usage.md).
That analyzer is not an automatic host adapter or a completed A/B evaluation.
