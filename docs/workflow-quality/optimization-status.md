# Spec Kit Plus optimization status

Checkpoint: 2026-09-18 (Asia/Tokyo). Baseline: `48cc022d52668a7433d0a8167585433883946c9c`.
This document consolidates the current workstream; earlier dated checkpoints are
historical measurements, not current whole-product acceptance.

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

## This increment: connect the tested pieces

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

## Validation executed at this checkpoint

Environment: Linux amd64, Go 1.23.2, Python 3.13.5, Git 2.47.3.
UTC timestamps in logs can fall on September 17; this checkpoint uses Tokyo time.

| Scope | Current result | Boundary |
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
