# Spec Kit Plus optimization status

Updated: 2026-09-18 (Asia/Tokyo). This compatibility increment follows
`2e9db45e29463996fdc2120711a8054b7a7b2116` on PR #120.

## Current decision

Keep the dependency order **#116 -> #119 -> #120**. Implementation and selected
path checks have progressed, but complete-runtime, installation, native-host and
release verification have not passed. Keep the PR draft; do not merge, publish,
upgrade installed projects or switch generated consumers based on this document.

This increment changes tests and this status page only. It adds no production
behavior, workflow, capability minimum, executor default or permission.

## Implemented work

| Area | Implemented | Not established by that implementation |
| --- | --- | --- |
| Quick execution/output | Explicit direct/worker selection, compact output, usage tools | A measured improvement in real accepted deliveries |
| Evaluation | Validated observations, unknown-value handling, fixed task fixtures | Actual Agent runs or independent human acceptance |
| Context | Bound compilation, strict decoding, exact state numbers and identifiers | Permission, live-source correctness or design approval |
| Shadow diagnostic | Optional CLI, explicit owner selection, shared capability discovery | A replacement executable contract or installed consumer adoption |
| Runtime reliability | Bounded/cancellable reads, output delivery and timeout handling | Rollback, descendant-process isolation or full-platform validation |
| Evidence | Required named tests, host package inventory and complete-log checks | Authenticity of edited logs or a run that never started |

The shadow report retains the complete owner packet. It does not authorize
execution, waive result submission, verify registered design approval or decide
product acceptance. Classic and Advanced remain separate prompt products with
unchanged defaults and minimum capability requirements.

## Latest compatibility checks

The new `quick_context_shadow_compatibility_test.go` adds three checks:

1. Remove only the explicitly added shadow help section/command, then compare
   the **whole** response with the legacy help owner for both --help and -h.
2. Put the shadow capability at every position in a mixed pack. Compare each
   item's usage, side effects, input/output and execution contracts with Show,
   preserving order, worker default, result submission and independent review.
3. Inspect a real fixture through help, Ensure, Pack, Show and the shadow reader;
   require unchanged project/Git files and no automatic execution action.

Linux amd64 / Go 1.23.2 selected-source results:

| Executed check | Result | Scope |
| --- | --- | --- |
| Prior baseline | 99 regular tests and one fuzz seed target passed with race detection | Rerun of the previous selected suite |
| Formerly excluded compatibility test bodies | 3 passed | General help, four selected legacy descriptors and mixed packs |
| New compatibility cases | 3 passed | Whole-help preservation, mixed contracts and read-only discovery |
| Combined selected suite | 105 regular tests plus one fuzz seed target passed; 220 passing events including subtests; no failures/skips | Not a complete runtime build |
| Same-scope go vet and new-file gofmt | Passed | Not whole-repository static checks |
| Deliberately broken local copies | Both rejected by the new tests | Synthetic help drift and missing worker contract, not discovered production bugs |

The local fixture now runs all sixteen named shadow entrypoint/state/process
case bodies. **This does not satisfy their complete-runtime gate.** The fixture
uses the retrieved legacy Quick help function and a deliberately restricted
legacy descriptor slice for api.ensure, quick.item-start, quick.item-accept and
artifact.show. Other descriptors, schema handlers and mutation owners are poison
seams and must not execute. SQLite is not linked. Those fixture slices/stubs are
not committed as replacement production implementations.

The three formerly excluded bodies are DiscoveryAgrees,
PreservesLegacyDescriptors and ShowSelectorsAndMixedPack (under the existing
TestQuickShadowCLIEntrypoint prefix). Their selected-path result is now known;
they still need execution against the fully linked runtime. Historical a59d67a
and 2e9db45 counts were 75 and 99 regular tests respectively, each plus a fuzz
seed target. Repetitions and subtests are not additional independent tests.

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
