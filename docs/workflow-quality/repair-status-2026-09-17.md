# Repair checkpoint: 2026-09-17

## Source and branch boundaries

The dependency chain remains #116 -> #119 -> #120. Source main and public
releases are unchanged. #119 head d62766ea contains the five runnable fixtures;
#120 now incorporates that head without discarding its existing context work.
Context source inspection began at 8937de27; original source/test blobs and
pyproject.toml were checked against GitHub Git blob identities before editing.
This checkpoint is not authorization to merge, publish or change permissions.

## Reproduced and repaired in this increment

| Issue | Repair |
| --- | --- |
| Distinct invalid UTF-8 strings produce the same normalized binding | Reject invalid UTF-8 in every bound text input before hashing |
| Oversized generated_at bypasses verification's byte ceiling | Validate the actual serialized packet size, not only the reconstructed request |
| Wire readers can silently accept duplicate/case-folded/unknown fields | Add strict DecodeBound with exact field names, types, unique keys and Unicode checks |
| Artifact path projection can disagree with its detailed bindings | Reconstruct and compare the packet's own canonical projection before freshness checks |
| Context schema is absent from wheel force-includes | Add the canonical schema at the matching core_pack relative path |

The first two defects and the missing package mapping were reproduced as failing
regressions before fixes. The strict wire API is an added defensive library
boundary; there is no claim that an installed Quick consumer previously used it.

## Validation actually executed

Linux amd64; Go 1.23.2; Python 3.13.5; available pytest 9.0.2. This was a
blob-verified partial source fixture, not a complete repository checkout or the
project's fully provisioned test-extra environment.

- Original context baseline: all 14 existing top-level tests passed.
- Updated context with race detection: 21 regular top-level tests plus one
  fuzz target's seed run passed; 86 passing events including nested tests,
  with zero failures/skips. These event counts are not 86 independent tests.
- `go vet ./context`: passed.
- Bounded fuzz run: 72,732 executions, no failure; not exhaustive proof.
- Three Python distribution/wire tests: passed. One reruns the same actual Go
  package in a temporary declared bundle layout; do not count that rerun as
  independent product coverage. Another validates actual Go-emitted JSON.
- Six uploaded source/test/config blobs matched the locally tested Git blob
  identities exactly. No dependency version or installed workflow changed.

Relevant commands from tools/specify-runtime:

```sh
go test -count=1 -race -json ./context
go vet ./context
go test ./context -run '^$' -fuzz FuzzDecodeBoundNeverReturnsPartial -fuzztime=3s -parallel=2
```

From the repository root:

```sh
python -m pytest tests/test_context_distribution.py
```

## Remaining blockers and resume point

The observed #119 CI run 35176957435 has seven failed jobs with no returned
steps or log URLs. Its cause is unknown; do not infer billing or code failure,
retry repeatedly, weaken checks, or call a configured native job a passing job.
Recheck final-head CI separately after a usable runner starts.

Next implementation: a read-only Quick shadow adapter using the real runtime
state/artifact owners, not caller-authored hashes. Then exercise installed
Classic/Advanced consumption and the complete runtime/SQLite/Work and Python
regressions in a complete checkout. Full wheel installation, native Windows/macOS,
real Agent benchmarks, cost/quality claims and release verification remain open.
The standalone context library, synthetic fixture checks and CI configuration
do not complete those tasks. No main merge or release occurred in this increment.
