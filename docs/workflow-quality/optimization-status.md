# Spec Kit Plus optimization status

Updated: 2026-09-18 (Asia/Tokyo). This installer-isolation increment follows
`b81a19b6e7ffca3dc9c640658bab87af6043bb04` on PR #120.

## Current decision

Keep the dependency order **#116 -> #119 -> #120**. Implementation and selected
path checks have progressed, but complete-runtime, installation, native-host and
release verification have not passed. Keep the PR draft; do not merge, publish,
upgrade installed projects or switch generated consumers based on this document.

This increment repairs Python runtime materialization and adds its regression
tests. No workflow, capability minimum, executor default or permission changes.
Existing installed binaries are not upgraded merely by this source commit.

## Implemented work

| Area | Implemented | Not established by that implementation |
| --- | --- | --- |
| Quick execution/output | Explicit direct/worker selection, compact output, usage tools | A measured improvement in real accepted deliveries |
| Evaluation | Validated observations, unknown-value handling, fixed task fixtures | Actual Agent runs or independent human acceptance |
| Context | Bound compilation, strict decoding, exact state numbers and identifiers | Permission, live-source correctness or design approval |
| Shadow diagnostic | Optional CLI, explicit owner selection, shared capability discovery | A replacement executable contract or installed consumer adoption |
| Runtime reliability | Bounded/cancellable reads, output delivery and timeout handling | Rollback, descendant-process isolation or full-platform validation |
| Installation | Independent verified binary copies and selected legacy-hardlink repair | A complete wheel/init/release or native-platform pass |
| Evidence | Required named tests, host package inventory and complete-log checks | Authenticity of edited logs or a run that never started |

The shadow report retains the complete owner packet. It does not authorize
execution, waive result submission, verify registered design approval or decide
product acceptance. Classic and Advanced remain separate prompt products with
unchanged defaults and minimum capability requirements.

## Latest installer isolation repair

The former hardlink optimization made the source, content-addressed cache and
multiple project binaries share writable file data. A real-file reproduction
showed that editing project A changed the cache, source and project B, and that
making the copy executable also changed source permissions.

`materialize_project_runtime_entrypoint` now uses independent copies. The private
helper retains its old name for compatibility but no longer creates hardlinks.
It keeps an exclusive candidate file open while copying, flushes/syncs it, checks
source identity and observable metadata drift, and verifies its expected SHA-256
before atomic replacement. Source permission bits are not modified and special
POSIX mode bits are not propagated. Candidate failures leave the old destination
intact and remove the temporary file. The cache uses the same existing safe-path
owner as project pins to reject symlink/junction traversal.

A matching digest is not sufficient for reuse: a multiply linked cache or
selected project pin is recopied on its next normal materialization. Independent
matching files remain reusable without a new copy. Other project directories are
not scanned or silently upgraded. An old, unselected linked project still needs
its own normal materialization before its remaining links are detached.

There is a storage/copying cost per independent project binary. This is deliberate
isolation, not a performance improvement claim. Already corrupted old pins are
not certified safe by detachment; use the existing validated runtime source and
installation/repair path. This is not hostile-writer isolation or a transaction
across cache, project binary, ignore files and launcher configuration. A verified
cache copy may remain when a later project write fails; no rollback is claimed.

Current Linux / Python 3.13.5 / Go 1.23.2 checks: **25 new test cases and three
unchanged existing materialization test bodies passed**, with zero failures or
skips. They use actual files, hardlinks, modes, symlinks, injected copy/flush/
replacement failures and the original atomic_io implementation. A tiny native
Go executable was built, pinned and executed successfully; it is a test fixture,
not the complete Specify runtime or a release asset. The earlier original-code
run of the initial 22 cases had 15 failures and seven passes, including expected
failures for the new API/guards as well as the reproduced shared-file defects.

The full installer module was imported and syntax-checked, not replaced by
extracted helper implementations. Local package initialization and two unrelated
launcher entrypoints are poison seams; they are not used by materialization and
are not committed. Whole `specify init`, launcher persistence, wheel construction,
public download and Windows/macOS execution remain unverified. No network
installation, credential lookup, profile switch or publication ran in these tests.

Historical compatibility checkpoint b81a19b: 105 selected Go cases plus a fuzz
seed target passed. All sixteen named shadow test bodies ran only against a
partial fixture with restricted legacy descriptors and no SQLite link. Those
results were not rerun or upgraded to complete-runtime evidence by this change.

## Remaining acceptance gates

| Gate | Current state | Required next evidence |
| --- | --- | --- |
| Complete Go runtime, SQLite/Work, API and all named tests | Not validated | Clean complete checkout, prepared dependencies, original full suite |
| Python, wheel/install and installed Classic/Advanced | Not validated | Existing suites against the same source revision |
| Native Windows/macOS | Not executed in this environment | Actual native run logs, not cross-compilation or workflow configuration |
| Cloud CI | Latest inspected baseline failed without returned steps | Accessible Actions annotation and actual execution; root cause remains unknown |
| Live source and registered design inputs | Not verified by the diagnostic | Existing source/design owners before any projection adoption |
| Real Agent quality/cost | Not measured | Comparable repeated runs, real instrumentation and independent acceptance |
| Main/release/distributed consumer path | Not performed | Passing gates, separate authorization and consumer verification |

The container still has no complete source/dependency checkout and cannot resolve
GitHub/Go-proxy hosts. Reading the failure annotation through the available
connector was rejected. No billing diagnosis, disabled check, repeated rerun or
permission change is justified by those observations. The current focused tests
cannot replace the complete-checkout verifier.

The initial review's broader document/large-file restructuring and measured
adaptive-execution rollout are also not implicitly complete. This page replaces
repetitive progress narration, not any runtime, release or acceptance contract.

## Resume through the existing validation path

In a clean prepared checkout, with a new output directory outside the repository:

```sh
python tools/workflow-quality/verify_quick_rollout.py --output-dir ../quick-rollout-evidence
```

Targeted race checks before that full run:

```sh
cd tools/specify-runtime
go test -race -count=1 -run '^TestQuickShadow(CLI|Compatibility)' .
go test -count=1 ./...
go vet ./...
```

The verifier requires prepared Python tools, this checkout's specify_cli and
cached Go dependencies. It does not install dependencies, authorize release or
accept partial source as a complete checkout. Keep source private, preserve user
changes and do not reapply superseded cumulative patches.

See [CI recovery](../ci-troubleshooting.md),
[command usage](../architecture/quick-shadow-cli.md) and
[runtime maintenance](../agent-guidance/workflow-maintenance.md).
