# Quick shadow state-read checkpoint — 2026-09-17

## Scope and reproduced failures

Parent: 7ba909455e1ca7f356a014a008029054ab08aff4, PR #120, stacked on #119 and #116.
This is a correction to the optional read-only diagnostic, not a generated
workflow switch, a new state machine, a release or execution authorization.

Three failures were reproduced before changing production code:

1. The typed confirmation read changed `9007199254740993` to
   `9007199254740992`, and shortened `0.12345678901234567890123456789` to
   `0.12345678901234568`. Exact dynamic metadata could therefore fail its stored
   decision digest or lose fidelity on a downstream JSON round trip.
2. Distinct JSON keys `confirmation_state` / `Confirmation_State` and nested
   `status` / `Status` passed the duplicate-key precheck but encoding/json's
   typed case-insensitive lookup accepted the later value. Staged/blocked
   source fields could look confirmed/pending in a shadow view. This is a
   diagnostic admission defect, not a claim that this command granted execution.
3. The original item-accept path sets newly unblocked work items to `ready`,
   but shadow admission allowed only pending/in_progress. A normal ready
   successor was incorrectly blocked even with an accepted prerequisite.

## Corrections

`decodeQuickShadowConfirmation` reuses the existing bounded, duplicate-aware
Unicode-safe JSON guard and adds exact typed-field-name checks before decoding.
It uses `UseNumber` for dynamic metadata, preserving source numeric lexemes
rather than converting them through float64. The raw source bytes, stored digest,
state and item order are never changed. The existing schema/digest checks still
run afterward; a mismatched digest is not recalculated or silently repaired.
Noncanonical externally reformatted numeric tokens must still match their stored
decision digest; this diagnostic does not migrate or re-confirm old records.

Field-name auditing follows the actual typed owner declarations, including
pointer fields and arrays. It rejects Unicode case aliases as well as ASCII
case aliases. Dynamic metadata maps retain distinct keys such as `Status` and
`status`. Unknown non-alias fields retain the original typed-owner behavior;
they remain covered by the original raw-state hash, not newly interpreted.

The selected status check now permits ready. Accepted, blocked, empty and
unknown selected statuses, duplicate/undeclared rows and dispatch blockers
remain rejected. The unchanged original packet builder still rejects unaccepted
prerequisites and an unconfirmed checkpoint, and retains result submission.
The obsolete pre-registration comment in the compatibility wrapper is corrected.

## Validation executed in this increment

Environment: Linux amd64, Go 1.23.2, Git 2.47.3, Python 3.13.5. The earlier
artifact manifests were verified before reusing their source. Container DNS
for GitHub and the Go proxy remained unavailable; no complete repository or
prepared dependency environment was obtained.

| Check | Result and boundary |
| --- | --- |
| Pre-fix regressions | Numeric/case-alias tests and ready-admission test failed as described above |
| New selected-source suite | 13 regular top-level tests plus one fuzz seed target passed with race detection; 36 pass events including subtests; zero failures/skips |
| Earlier command/discovery suite rerun | 36 regular top-level tests; 86 pass events including subtests; zero failures/skips, race enabled |
| Static checks | go vet passed on the new selected-source suite; changed Go files passed gofmt |
| Bounded fuzz run | 160,714 executions without failure; not exhaustive proof |
| Whole-runtime integration tests | Three new actual-Run/Git/file tests supplied, not executed in a complete runtime here |

The new selected-source fixture uses the retrieved Quick owner declarations,
original digest and packet/checkpoint/dependency functions, the exact final
admission function, and the existing strict JSON guard functions. It exercises
exact decoding through the original decision hash and worker-packet JSON output.
It does not implement a substitute state machine or model real user approval.
The fixture and its selected-source provenance are evidence artifacts only;
they are not committed as product code. Neither test event counts nor the
older suite's rerun are new independent product acceptance evidence.

The three new integration tests use the existing `Run`, `shadowTestRepo`, real
Git/files and the normal confirmation writer. They cover a ready successor,
retained prerequisite rejection, precise numbers in the returned JSON, and
alias rejection without source repair. The existing ten entrypoint tests plus
these three still require complete-runtime execution. No whole Go/SQLite/Work,
Python/install, Classic/Advanced, native Windows/macOS, real Agent benchmark,
CI success, main merge or published binary upgrade is claimed.

## Resume point

In a complete prepared checkout, execute the relevant real entrypoints and then
all existing regressions:

```sh
cd tools/specify-runtime
go test -race -count=1 -run '^TestQuickShadowCLI(State|Entrypoint)' .
go test -race -count=1 -run '^TestQuick(Shadow|ContextShadow)' .
go test -count=1 ./...
go vet ./...
```

Then perform Python, package/install and native-OS checks. Resolve exact live
artifacts and registered approvals before any generated consumer adopts the
projection. Obtain actual runnable CI evidence rather than weakening checks or
inferring a root cause from empty step lists. Current cloud CI and the complete
installation path remain separate, unverified gates.
