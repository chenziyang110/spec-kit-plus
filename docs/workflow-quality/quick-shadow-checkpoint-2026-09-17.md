# Quick shadow checkpoint: 2026-09-17

## Change boundary

Base: `d8d39b980b07509d4198cb409c3de350a032bf56`, PR #120, stacked on #119 and #116.
This increment completes the previously uploaded but uncommitted shadow drafts.
It adds an internal Quick adapter and tests, not a new public command, generated
workflow consumer, permission gate, persisted artifact or release. No main merge,
profile-default change, source publication or forced branch update is part of it.

## Implemented and corrected

The adapter resolves the real local project/worktree and Git HEAD, securely
locates one existing Quick confirmation file, reads bounded bytes and decodes
the owning type. It invokes the existing decision-digest and worker-packet
functions and keeps the entire returned owner packet. It binds the raw file,
not just the decision digest: write-scope, timestamp and execution changes can
invalidate a report even when the decision digest remains unchanged.

Four failing regression cases were reproduced against the earlier adapter draft:
duplicate status rows and blocked, unknown or empty selected statuses incorrectly
produced a report. The new admission check rejects them, plus undeclared status
rows and selected dispatch blockers. Absent rows retain the existing pending
default; this never means a dependency is accepted. The old workflow is unchanged.

An unbounded reread through the legacy loader was removed from the adapter.
Tests compare the bounded path against the actual loader and packet builder.
Observable state/Git changes, symlinks, malformed/oversized JSON, missing HEAD,
parent-repository selection and ambient Git overrides fail without data repair.
Linked worktrees with the same HEAD still have distinct report identities.

Assembly now compiles the bound projection once rather than twice. The second
snapshot still validates identity and canonical wire input and compares the
complete source fingerprint. Tests compare every returned field against the
two-projection reference (excluding only the informational timestamp), exercise
callback aliasing and preserve future opaque owner fields and integer precision.

## Validation actually performed

Linux amd64; Go 1.23.2; Git 2.47.3. Container network access was unavailable.
The local fixture had eight unchanged context source files plus go.mod and
project_path.go checked against their Git blob SHAs. Main-package checks used
selected owner declarations copied from the retrieved Quick sources, including
types, loader, decision digest and packet builder, in a LOCAL test-only file.
That file is not committed and is not a substitute full runtime implementation.
This is a partial source-slice validation, not a full repository checkout/test.
The previous context test suite was not rerun in full in this increment.

| Check | Observed result |
| --- | --- |
| New shadow library tests with race detection | 10 regular top-level tests plus one fuzz seed group; 32 passing events including subtests |
| New main-package adapter tests with race detection | 10 top-level tests; 25 passing events including subtests, using actual Git/files and selected owner code |
| Failure/skip counts in the final focused runs | Zero failures, zero skips |
| Static checks | go vet passed on the shadow package and the selected main-package test source |
| Final bounded fuzz run | 112,005 executions without failure; not exhaustive proof |
| Upload integrity | Five source/test blobs matched the exact locally tested bytes |

Counts include no earlier session tests. Subtest events are not additional
independent tests. Fixture confirmations are synthetic; they do not establish
human acceptance or real-project workflow success.

## Assembly microbenchmark

Five samples per mode, 150 iterations each, same Linux process environment.
The comparison is against the test-only two-projection reference algorithm,
not a released product baseline. Payload size is an added synthetic deliverable.

| Added payload | Two-projection median B/op | One-projection median B/op | Reduction |
| --- | ---: | ---: | ---: |
| 0 bytes | 44,547 | 38,054 | 14.6% |
| 32,768 bytes | 690,135 | 605,430 | 12.3% |

Timing samples were noisy, especially for the smaller input. Do not extrapolate
them to production latency, Agent tokens, quality retention or filesystem cost.
The benchmark isolates assembly and excludes the adapter's Git/file reads.
The whole owner contract is deliberately retained; this is not prompt compression.

## Remaining verification and resume point

In a prepared complete checkout, from tools/specify-runtime:

```sh
go test -race -count=1 ./context
go test -race -count=1 -run '^TestQuickContextShadow' .
go test -count=1 ./...
go vet ./...
```

Then run the existing Python, package/install and Classic/Advanced regressions.
Native Windows/macOS execution, real Agent benchmarks and working cloud CI remain
unverified. Check the exact new head's run; the older empty-step failures do not
identify their cause, and supplied tests/configuration are not successful runs.
Do not bypass checks, infer billing failures, repeatedly rerun without evidence,
or publish a version to work around those gaps.

Next implementation boundary: read-only CLI/capability discovery with explicit
shadow semantics, then exact live artifact/registered-approval resolution before
any generated consumer switches. The current report has authorizes_execution=false
and live_code_verified=false. It proves neither real source behavior nor product
acceptance. Preserve complete UI/design, permission, result, Review and human
acceptance contracts. Repeated reads are not a transaction or hostile-writer sandbox.
