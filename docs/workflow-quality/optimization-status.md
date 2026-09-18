# Spec Kit Plus optimization status

Checkpoint: 2026-09-18 (Asia/Tokyo). Baseline: `48cc022d52668a7433d0a8167585433883946c9c`.
The latest follow-up below supersedes the validation summary for changed API
paths. Earlier checkpoint measurements are historical, not whole-product acceptance.

## Delivery boundary

The dependency chain is #116 -> #119 -> #120. Changes remain on their existing
feature branches. Main merge, release publication, installed upgrades and
switching generated consumers are separate, uncompleted gates.

Implemented in the chain: Quick output/execution improvements and usage tools;
validated evaluation records and reproducible fixtures; bound context assembly
and strict decoding; the optional read-only `quick.context-shadow` command and
its discovery contract; precise state decoding and ready-successor handling;
complete-test evidence inspection; cancellable reads and watchdog delivery fixes.
These implementations do not establish measured Agent cost reductions or final
product acceptance. No new feature/default change is introduced by this checkpoint.

## Historical a59d67a change: connect the tested pieces

Three new process-path regressions call the existing watchdog with **RunContext**,
not a replacement runner. They cover:

- Exact large integers/decimals and the complete owner packet across the actual
  Quick read path and final JSON output, with unchanged project/Git files.
- A real closed operating-system pipe returning delivery failure without
  changing the existing Quick state.
- An observed Git helper process that blocks, receives the real parent timeout,
  and returns through the adapter. The final response has no late report, no
  automatic retry, and does not claim rollback or descendant cleanup.

The existing rollout verifier now requires **16** named shadow cases: the prior
13 entrypoint/state cases plus these three process cases. Existing lifecycle,
context, package-inventory and installation gates remain intact. Missing any of
the newly required cases is tested as a failure. No additional verifier is added.

## Historical a59d67a integration validation

Environment: Linux amd64, Go 1.23.2, Python 3.13.5, Git 2.47.3.
UTC timestamps in logs can fall on September 17; this checkpoint uses Tokyo time.

| Scope | Result at that checkpoint | Boundary |
| --- | --- | --- |
| Combined selected-source Go suite | 75 regular top-level tests and one fuzz seed target passed with race detection | Not the complete runtime package or all repository tests |
| Original entrypoint/state cases in that suite | 10 of the prior 13 executed successfully | The three API/general-help cases below were not selected |
| New watchdog -> RunContext -> Quick process cases | 3 of 3 executed successfully | Test-file additions still need the full-checkout run |
| Same selected-source Go static checks | Passed | Not full runtime vet |
| Verification-tool Python suite | 65 pytest cases and 29 unittest subtests passed | Tests the verifier, not product Go/Python/install suites |
| Full-source rollout preflight | Blocked before product gates | Complete source and prepared dependencies are unavailable here |

The Go fixture contains byte-verified production adapter/command/Git/decoder,
context and watchdog files, original Envelope/path owners, and exact selected
function bodies for Run/RunContext, JSON/argv binding, Quick types/digest/packet
and prerequisite checks. It uses real temporary files and Git processes.
**Unrelated command/API owners are poison stubs and must never run.** Therefore
this is integrated selected-source execution, not a complete source build. Those
stubs and the partial fixture are delivery evidence only; they are not committed
as a replacement runtime or used to satisfy the full-source verifier.

The three original entrypoint tests not executed in the combined fixture are:
`TestQuickShadowCLIEntrypointDiscoveryAgrees`,
`TestQuickShadowCLIEntrypointPreservesLegacyDescriptors`, and
`TestQuickShadowCLIEntrypointShowSelectorsAndMixedPack`.
Their narrower discovery-helper tests did run, but do not replace these cases.
All 16 required cases must be rerun together in the complete real runtime before
claiming whole-runtime verification. Repetition and subtest counts are not added
to the number of independent tests.

## Remaining work: do not relabel as completed

| Gate | Actual state | Resume condition |
| --- | --- | --- |
| Complete Go runtime, SQLite/Work and all entrypoints | Not validated | Prepared complete source checkout, dependencies and clean worktree |
| Full Python, wheel/install and installed profiles | Not validated | Run existing suites against the same source revision |
| Native Windows/macOS | Not executed here | Obtain real native job logs; configuration/cross-compilation is not native execution |
| Cloud CI | Latest observed baseline run failed before returned steps | Read the Actions annotation and resolve its actual cause; do not infer billing |
| Live source/registered design input verification | Not implemented by the shadow diagnostic | Use the existing owners before any generated consumer adopts its projection |
| Real Agent quality/cost benchmark | Not executed | Comparable runs, actual instrumentation, independent acceptance; unknown cost is not zero |
| Main merge/release/distributed consumer verification | Not performed | Passing gates and separate authorization |

The broader initial review also proposed large-file/document restructuring and
measured adaptive execution rollout. Those are not completed merely because the
read-only diagnostic works. Avoid starting another speculative feature while the
integration and CI gates above remain unresolved.

## Resume with the existing commands

In a prepared complete checkout at the desired source revision:

```sh
python tools/workflow-quality/verify_quick_rollout.py --output-dir ../quick-rollout-evidence
```

The output directory must be new and outside the checkout. The checker requires
the existing prepared Python environment (including Ruff and this checkout's
specify_cli) and cached Go dependencies. It neither installs dependencies nor
changes repository settings. For targeted race checks before the full run:

```sh
cd tools/specify-runtime
go test -race -count=1 -run '^TestQuickShadowCLI' .
go test -count=1 ./...
go vet ./...
```

The complete rollout checker, original CI checks and native jobs remain the
acceptance path. A partial reproduction package is not a substitute checkout.
Keep source private, preserve existing state and user edits, and do not reapply
old cumulative patches over the feature branch.

## 2026-09-18 follow-up: capability API boundaries

Parent source: `a59d67a0e82df0900eb2310eb69e33dabe2bc2cf`. The production change
is limited to the existing capability API owner; no new command or workflow.

Reproduced at the actual selected Run -> API path: a duplicate JSON selector
silently replaced an unavailable capability with an available one; Pack emitted
132,788 bytes when its runtime-identity metadata was expanded; Ensure emitted
143,912 bytes for an input below its limit that repeated an unknown ID in output.
The previous items-only limit missed both complete-response cases.

The repair rejects duplicate/alias selectors and invalid UTF-8, bounds all
capability-input forms through the existing reader, and checks final serialized
Ensure/Pack envelopes. Oversize responses contain no partial contracts. External
write failures are reported without retry; bytes already written cannot be
retracted. Caller data is not changed. Normal selection order,
metadata compatibility, output contracts, status codes and argv binding remain.
The old separate items serialization is removed; no speedup metric is claimed.

Validation: 24 new top-level tests passed (18 boundary/real-file/stdin checks and
six Run/API-route cases). The combined selected-source suite passed **99 regular
top-level tests plus one fuzz seed target**, with race detection, 212 passing
events including subtests, zero failures/skips; same-scope vet passed. Counts
include previous integration reruns, not 99 new tests. Fuzz seeds are not a new
randomized fuzz run. Before-fix failures are preserved in the delivery evidence.

This run type-checks the whole modified capability_efficiency.go, the unchanged
buildinfo implementation, shared JSON input and original output/path owners.
The Run/API dispatcher, flags, registry and contract helpers are exact selected
source. Store contributes only its retrieved SchemaVersion constant; SQLite is
not linked. Unselected legacy descriptor, schema and non-Quick owners remain
poison test stubs in the LOCAL fixture and are not committed. Valid shadow
Show/Pack/Ensure/help interaction did execute without those stubs being called.
This is stronger selected-path validation, not a complete runtime build.

The three original legacy/general-help entrypoint cases listed above, complete
repository regressions, wheel/install, native hosts, CI execution and live
artifact/approval consumption remain unverified. No named verification gate is
removed or relabelled. Prior partial-source preflight blockers still apply;
source changes stay on PR #120 without main merge, release or consumer adoption.
