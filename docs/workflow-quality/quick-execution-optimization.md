# Quick execution: compact responses and truthful resume

## Scope and status

This incremental source change preserves the Quick checkpoint, worker-result,
write-scope, Work/fence, dependency, source-continuity, and closeout gates. It
neither changes delegation policy nor releases a runtime binary. Classic and
Advanced keep their existing default responses and generated instructions.

This is an opt-in source experiment. The stdlib-only helper tests and synthetic
serialization benchmark were run locally; the full-package integration tests
and installed consumer rollout remain unverified. Before consumer rollout,
publish the new flag through `quick --help` and `api show`, verify both workflow
profiles, and follow the release/installer compatibility process. Do not infer
runtime support from the presence of this document.

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
If any replacement binding is missing, the response stays full.

All other fields are retained, including the current packet, packet path,
Work claim, worker requirement/proof, inline reason, complete scheduling sets,
blockers, and next action. False and empty values are not silently removed.
Errors retain their existing complete diagnostics. Compact output is intended
for a hot execution loop after intake, not as a substitute for reading the
confirmed scope, original inputs, task packet, or applicable UI contracts.

For a full read-only context refresh, run the existing command without the flag:

```sh
specify-runtime quick item-status <id> --format json
```

Do not retry a mutation merely to obtain a larger response. Generated prompts
are deliberately unchanged until runtime discovery and end-to-end verification
are complete.

## Resume failure handling

Resuming an in-progress item must persist confirmation before updating the
STATUS projection. Both failures are now reported with their persistence phase
and underlying error. A failed resume returns no successful dispatch receipt.
The existing Work claim and in-progress task are retained: repair the I/O
failure, then retry with the same guarded Work identity. This deliberately does
not release ownership over a potentially dirty workspace or claim that the two
files are a single atomic transaction.

## Reproducible validation

The pure response/persistence helpers use only the Go standard library:

```sh
cd tools/specify-runtime
go test -count=1 -v quick_execution_response.go quick_execution_resume.go \
  quick_execution_response_test.go quick_execution_resume_test.go
go test -race -count=1 quick_execution_response.go quick_execution_resume.go \
  quick_execution_response_test.go quick_execution_resume_test.go
go test -run '^$' -bench BenchmarkQuickExecutionResponse -benchmem \
  quick_execution_response.go quick_execution_resume.go \
  quick_execution_response_test.go quick_execution_resume_test.go
```

Full-package integration tests additionally exercise real Quick commands,
the unchanged worker-result gate, legacy output, injected STATUS projection
failure, and retry under the same Work identity. These were authored against
existing repository fixtures but have not been run in this environment:

```sh
go test -count=1 -run 'TestQuick(Compact|Resume)' .
go test -count=1 ./...
```

The response-size experiment is synthetic and measures serialized **data bytes**,
not complete envelopes, live agent token usage, cache behavior, end-to-end
latency, quality retention, or API cost. Keep benchmark results separate from
real workload A/B evaluation. Reduced duplicate output does not eliminate the
cost of building full state in memory, and complete scheduling lists still
scale with task count.
