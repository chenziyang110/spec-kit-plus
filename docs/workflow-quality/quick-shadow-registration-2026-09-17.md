# Quick shadow registration checkpoint — 2026-09-17

## Change boundary

Parent: 70d846cd72e32532a06571a37e7fef66437805f2, PR #120, stacked on #119 and #116.
This increment registers the already-landed optional diagnostic, not an executor,
workflow consumer, release or new permission grant. Main and published binaries
are not updated. Earlier local cumulative/remaining patches are superseded.

## What is now connected

- Run/RunContext routes Quick through runQuickWithContext, preserving cancellation.
- Explicit context-shadow invokes the strict parser before legacy help handling.
- Generic Quick help retains its owner response and adds only the new command
  and output contract. No workspace enumeration, task selection or state write.
- One capability ID and summary connect Handshake/List/Ensure to the diagnostic.
- API Show and Pack use the same dedicated descriptor dispatcher. Other IDs
  delegate byte-for-byte to their existing runAPIShow owner; the schema switch
  and ordinary Quick implementation are unchanged.
- Compact packs retain the diagnostic's output contract. Read-only and mutation
  capabilities keep distinct side effects in mixed packs.
- Only quick context-shadow gains the short query timeout classification.
- Current architecture/core/command guides agree on registered-but-not-released.

The complete legacy owner packet remains present. Execution, live source,
registered design approval and acceptance are not established by a shadow report.
No minimum installed capability, Classic/Advanced prompt or execution default
has been changed. Old binaries must advertise this optional capability before use.

## Tests actually executed

Linux amd64, Go 1.23.2, Git 2.47.3, Python 3.13.5. Direct container DNS for GitHub
remained unavailable and no complete source checkout/dependency cache existed.
Do not interpret these results as a successful full runtime build.

1. Original 27 command/Git/cancellation/reader tests rerun with race detection:
   passed, zero failures/skips.
2. Those 27 plus nine new discovery helper tests: 36 top-level tests, 86 passing
   events including subtests, zero failures/skips, with race detection. Vet
   passed on the same selected source. These are not 86 independent tests.
3. Two existing no-owner-access entrypoint test bodies executed with race
   detection against the exact modified Run/RunContext source and actual CLI
   handler/core: help before repository access and pre-cancelled invocation.
   Unselected command owners and the state-reader seam were poisoned test stubs
   that panic if called. Argv pinning was stubbed. This proves only those no-read
   routing paths; it is NOT execution of the full product entrypoint suite.
4. Full original main.go, capability_efficiency.go, command_timeout.go and
   context-compiler.md were matched against their Git blob identities before
   editing. The earlier delivery archive's SHA-256 manifest was checked.
5. Changed Go files parsed/formatted successfully. Ten complete-checkout
   integration tests are supplied, including the prior eight and two added
   legacy-descriptor/mixed-pack checks. Their complete-runtime execution is
   pending; the two selected smoke bodies do not replace that gate.

The new helper tests cover preserving existing help fields and large integers,
no duplicate command advertisement, cancellation before the old help owner,
invalid/trailing JSON, full augmented-output bounds, legacy failure forwarding,
selector forwarding, shared descriptor restrictions and exactly one registry ID.
Production helpers are extracted unchanged for the selected-source fixture.
No fake Quick state machine or alternate implementation is committed.

## Remaining gates

In a complete prepared checkout, run:

```sh
cd tools/specify-runtime
go test -race -count=1 -run '^TestQuickShadowCLIEntrypoint' .
go test -race -count=1 -run '^TestQuick(Shadow|ContextShadow)' .
go test -count=1 ./...
go vet ./...
```

Then complete Python, wheel/install, Classic/Advanced and native Windows/macOS
checks. Resolve exact live artifacts and registered approvals before any consumer
adopts the context projection. Real Agent metrics and independent acceptance
remain separate from diagnostic correctness. Recheck final-head cloud CI; prior
empty-step failures and inaccessible annotations do not establish their cause.
Do not remove checks, infer billing, retry repeatedly without evidence or release
just to work around infrastructure limits. Merge and publication remain separate.
