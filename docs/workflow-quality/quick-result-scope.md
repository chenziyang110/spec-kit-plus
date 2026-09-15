# Quick worker-result scope validation

## Scope

This source change repairs the lexical check used by
`requireQuickWorkerAcceptProof` before first worker-result acceptance. It does
not enable compact output, change delegation or human checkpoints, create a
Work identity, expand write authority, or release a runtime binary.

An empty packet `write_scope` means no-write work. It may be paired with an empty
reported changed-file list, but it must not authorize arbitrary changed files.
The former validator returned success for every result when that scope was
empty. It also compared unnormalized prefixes, accepting a reported path such
as `src/../outside.go` against the scope `src`.

The two existing scope functions now live in `quick_execution_scope.go`.
They reject parent traversal in either slash convention, absolute/drive/UNC
and stream-qualified paths, project-root scopes, embedded wildcards and
malformed or control-character-bearing paths. Scope entries are normalized once
per result. Exact paths, bounded directory descendants, leading `./`, Unicode,
spaces inside path segments, literal bracket routes and the existing final
`/**` / legacy `/*` descendant semantics remain supported. Malformed sibling
scopes fail closed rather than being ignored. Caller-owned slices are unchanged.

## Boundaries

This validator receives the result reader's normalized string list, not the
original raw JSON. The common result normalizer already trims strings and drops
blank list entries. A modifying worker whose entries all normalize away still
fails the existing nonempty-changed-files proof check. This change does not make
that shared normalizer strict, and does not claim rejection of every malformed
raw result representation.

The check is lexical, not a filesystem sandbox: it does not resolve symlinks,
reparse points, target-specific filename aliases, renames or actual Git changes.
Work/fence/claim checks and independent actual-delta auditing remain necessary.
It does not retroactively re-audit an already accepted item or redesign the
inline fallback. No change is made to authority, result matching, source
continuity, queue reporting, closeout or prompt generation.

## Validation

Executed locally using the exact production lexical validator, without service
or registry substitutes:

```sh
cd tools/specify-runtime
GO111MODULE=off go test -race -count=1 -v quick_execution_scope.go quick_execution_scope_test.go
GO111MODULE=off go vet quick_execution_scope.go quick_execution_scope_test.go
GO111MODULE=off go test -run '^$' -fuzz '^FuzzQuickScopeNeverAcceptsTraversal$' -fuzztime=3s -parallel=2 quick_execution_scope.go quick_execution_scope_test.go
```

The regular suite contains 31 rejection cases and 16 compatibility cases, plus
one diagnostic test and five fuzz seeds. The old production functions were
extracted byte-for-byte (no stub implementations) and reproduce failures under
these tests. Windows amd64 test-binary cross-compilation also succeeded; this is
not a native Windows execution result. Fuzz execution counts are not a workflow
quality or cost metric.

A full-package `TestQuickScopeWorkerProofGate` additionally exercises the real
worker-result file reader and proof gate. It is supplied but has **not** been
executed in this environment, which lacks a complete checkout and dependency
cache. Full verification remains required:

```sh
go test -count=1 -run 'TestQuickScope' .
go test -count=1 ./...
go vet ./...
```

No complete runtime, installed-profile, CI or real-agent pass is claimed.
No token-saving, latency, security-completeness or quality-retention percentage
is inferred from these tests.
