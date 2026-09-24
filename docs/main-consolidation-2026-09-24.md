# Main consolidation — 2026-09-24

## Scope and source snapshots

The requested maintenance covers the nine open pull requests, two open issues,
and 48 non-default branches observed at the start of the review.

- Initial `main`: `ca952eb64a6a2bc873bfd577d5a945d8a29e3679`.
- Complete feature stack: `d53c660b36974162297b2f37441d0bf89337c08c`
  (#120, with #119 and #116 in its ancestry).
- `main` after the five compatible dependency merges:
  `b6e6cbfb1fefa7f3f1c5b029c52e108367621bc2`.
- Source remains private. Runtime release publication is outside this maintenance.

## Pull request and issue decisions

| Item | Decision and resulting behavior |
| --- | --- |
| #98, #100, #108, #117, #118 | Accept `actions/stale` 11, packaging 26.3, Click 8.5, pinned setup-uv 10.1.0, and MCP 2.2 with `<3`. The Click missing-argument assertion accepts quote/case differences while retaining exit-code and diagnostic checks. |
| #99 | Close the incompatible `pydantic-graph<3` upgrade. Existing `Graph(nodes=...)` and `node_defs` consumers require the current `<2` constraint; a GraphBuilder migration needs separate implementation and validation. |
| #116, #119, #120 | Consolidate the continuous feature stack through #120, including this reviewed integration repair. Retain every original feature commit in ancestry. |
| #112 | Add guarded `tasks rebind`, immutable history, lifecycle-preserving artifact refresh, stale-stage rejection, schema/discovery support, and Classic/Advanced instructions and installer coverage. |
| #115 | Retain the existing UI-only task-reopen fix from `fb9d95e19860ae0cec8d8449cb542daf2b0a169b`; add an end-to-end public-command regression for failed UI acceptance, reopen, corrected evidence, and successful acceptance. |

Integration repairs also cover two Go test compilation errors, portable rejection
of Windows drive paths, deterministic backslash normalization, secure symlink
rejection assertions, and current rendered Classic Quick delegation contracts.
Filesystem boundary tests use a real socket inode when the host denies socket
creation; their no-replacement and inode-identity checks remain enforced.

## Historical branch equivalence

Thirty-six of the 39 historical non-agent/non-Dependabot branch tips are strict
ancestors of the initial `main`. The other three have explicit dispositions:

- `codex/fix-pr-review-gates`: tip `83b79017eb8df536105a3d8a1f698509157fbbf4`
  and the #97 squash commit `544e009d93da90ccd43ccff4dd3139a846de5d35`
  have the identical tree `172d47fc7a7f276eb3d4a2b5182e367907b848a6`.
  The squash commit is already in `main`.
- `feat/graph-native-residual-cleanup-clean`: its four rewritten commits match
  the corresponding integrated commits by tree and patch. Tip
  `7186b46aacbddc2b0ae888b19f1a97c705534aec` matches integrated commit
  `d585d0f7f553300163d860ce32949289eaa9ef63` at tree
  `f172fd86b7bd1682dc89a39b07f339c2e39f927d`.
- `chore/release-v0.6.21`: the only divergent change replaces `0.6.21.dev0`
  with `0.6.21`; the current source is `0.8.5.dev0`. Annotated tag `v0.6.21`
  points to the exact branch tip and is retained.

## Reviewed branch tips

This inventory preserves recovery identifiers and the integration disposition.
Remote ref deletion is a separate operation whose completion must be verified
against the live branch list. The Click branch subsequently advanced to
`cb7787a3d0600d27a9eed2f2b84828fcd945f699` for its tested assertion repair.
The feature-stack branch advances when this integration repair is committed.

| Branch | Initial tip | Disposition |
| --- | --- | --- |
| `agent/context-compiler-20260916` | `d53c660b36974162297b2f37441d0bf89337c08c` | Feature stack: #120 (contains #119 and #116) |
| `agent/quick-adaptive-eval-20260916` | `d62766ea7d5bc9b59e37142ee19a6364aacdc46b` | Contained in #120; PR #119 |
| `agent/quick-runtime-optimization-20260914` | `06bc926c736cb3787fb07c279b5426aa3f3ff9ee` | Contained in #120; PR #116 |
| `chore/release-v0.5.3` | `03b92d6e91ffc8686454d6308d7a7914dd2d1d6f` | Already an ancestor of initial main |
| `chore/release-v0.5.4` | `8c69ea6ad10eb57e9c81c728abdd580df552a420` | Already an ancestor of initial main |
| `chore/release-v0.5.5` | `ce1b4f82df22019c73c107f48e6a146dd4715124` | Already an ancestor of initial main |
| `chore/release-v0.5.11` | `3f003d2bd26e4b4e73b77950c148ccb010ece90c` | Already an ancestor of initial main |
| `chore/release-v0.5.12` | `52d3c91234473ef5f5abe98c7792dbd0179ffa03` | Already an ancestor of initial main |
| `chore/release-v0.5.14` | `c9129b4c067623acb9dad9953e6c846876c0c934` | Already an ancestor of initial main |
| `chore/release-v0.5.15` | `cd0320b350ded213c1da4d6fc1465c64408f64ad` | Already an ancestor of initial main |
| `chore/release-v0.5.16` | `acc9b1b4a23717bb8f5dce1644c7c9db8cdf721b` | Already an ancestor of initial main |
| `chore/release-v0.5.17` | `61f6014f881d1afe464741e0da950cb2a803ef9f` | Already an ancestor of initial main |
| `chore/release-v0.5.20` | `70af8c538b8e082abd6049db8eb6fe4e59e95b95` | Already an ancestor of initial main |
| `chore/release-v0.6.0` | `f28cb9973cbb52b6900405032137a58a499418f6` | Already an ancestor of initial main |
| `chore/release-v0.6.5` | `b040430a57b1bcaad7d89335b979fa13c1b2b6c7` | Already an ancestor of initial main |
| `chore/release-v0.6.20` | `1f7e4f8b45dfe6913b7f5778a18b49bacec841c1` | Already an ancestor of initial main |
| `chore/release-v0.6.21` | `197818c6f63b55c95717fe55421000e5715c3c6e` | Superseded version bump; tip retained by v0.6.21 tag |
| `chore/release-v0.6.22` | `02d71e6db47c47d5881db27e342384d1c6591e0c` | Already an ancestor of initial main |
| `chore/release-v0.6.23` | `d5a442ac9ea53c0c143b564181f96ce36be74d26` | Already an ancestor of initial main |
| `chore/release-v0.8.0` | `174709ac270c254c787573c59fea118457c85da2` | Already an ancestor of initial main |
| `chore/release-v0.8.1` | `d76945681610536c7d9d0718873c87442916351d` | Already an ancestor of initial main |
| `codex/design-direction-checkpoint` | `e5e131c2d56edf70d0efec29fb548d6b1e5c391c` | Already an ancestor of initial main |
| `codex/discussion-checkpoint-prefix` | `5e7e544349b10e622c5444266e802bda54f5d760` | Already an ancestor of initial main |
| `codex/document-public-runtime-release` | `3db1115e60d23af3a5d30636d3090f96aaab4ebb` | Already an ancestor of initial main |
| `codex/fix-map-scan-build` | `46f91235931e1dfc9c9a5f0f65c18a25685d772d` | Already an ancestor of initial main |
| `codex/fix-pr-review-gates` | `83b79017eb8df536105a3d8a1f698509157fbbf4` | Squash-equivalent: #97; see evidence below |
| `codex/fix-windows-cursor-init` | `21a7aec033156bbe5265a65cc983c9a9509ec58f` | Already an ancestor of initial main |
| `codex/public-runtime-releases` | `78afefbc96cc2496cc2d9ff9618479a63c8e32a8` | Already an ancestor of initial main |
| `codex/release-v0.7.0` | `09e4c37190ae0c22e5a8451e84485469556aa086` | Already an ancestor of initial main |
| `codex/remove-clarify` | `31c02674556387ba0fa76cc8e3b32bf267874d14` | Already an ancestor of initial main |
| `codex/sp-run-control-core` | `8b2a7eff48726a8e8cbd6764036addb37caf743a` | Already an ancestor of initial main |
| `codex/sp-run-control-recovery` | `4f7f349ac6df4914456eda371ed7f8665832bab2` | Already an ancestor of initial main |
| `dependabot/github_actions/actions/stale-11` | `d9573c4696aec888a6a88ce91a05d2acab930355` | Merged: #98 |
| `dependabot/github_actions/astral-sh/setup-uv-10.1.0` | `992c2919442f424283d8064ae9cd92f4e6cd66c4` | Merged: #117; all three stack invocations synchronized |
| `dependabot/pip/click-gte-8.5.0` | `6ad68c92173558e4a5a6fcdddd7171eb701e3a3a` | Merged: #108 after CLI assertion repair |
| `dependabot/pip/mcp-gte-2.2.0-and-lt-3` | `8cc948845d5c4fd3d299def094a8e904daf7958c` | Merged: #118 |
| `dependabot/pip/packaging-gte-26.3` | `4b50f0448b06181564e80a2eec5b9b094f9bed48` | Merged: #100 |
| `dependabot/pip/pydantic-graph-lt-3` | `81b80795e21713af4635b447509017d7fc75298a` | Closed: #99; incompatible major upgrade rejected |
| `feat/downstream-testing-control-plane` | `997cb77e89e00b11fd32818f969c64593ea3bb41` | Already an ancestor of initial main |
| `feat/downstream-testing-control-plane-fix` | `3ff5add7cff4e69a8a87b853e012fc8057a5533d` | Already an ancestor of initial main |
| `feat/downstream-testing-control-plane-worktree` | `c13f10dfa3ee26bf3456428850a1a430e889b6a6` | Already an ancestor of initial main |
| `feat/graph-native-baseline-sync` | `c6be719dfcd8b08d6b76425b3e3794bf4816963f` | Already an ancestor of initial main |
| `feat/graph-native-residual-cleanup` | `d585d0f7f553300163d860ce32949289eaa9ef63` | Already an ancestor of initial main |
| `feat/graph-native-residual-cleanup-clean` | `7186b46aacbddc2b0ae888b19f1a97c705534aec` | Tree/patch-equivalent rewritten history; see below |
| `feat/sp-debug-expanded-observer-runtime-logs` | `1459209e71e48380c3bcd010d19e8c400646f443` | Already an ancestor of initial main |
| `feat/sp-specify-fixed-heavy-discovery` | `db3944e420b87b04de0b8fe70907b14092e40a9b` | Already an ancestor of initial main |
| `feat/unified-scan-freshness` | `dcc2576fa8a3fec78779d1435007222a8e8c27c7` | Already an ancestor of initial main |
| `sp-debug-dual-observer` | `634ed0aa1d0a71df489637ec0b0f1a4bf975dc65` | Already an ancestor of initial main |

## Verification evidence and limits

Local verification used Python 3.12.14 and Go 1.23.2 on Linux, with the actual
Click 8.5.0, packaging 26.3, MCP 2.2.0, and pydantic-graph 1.107.6 dependencies.

| Check | Result |
| --- | --- |
| Changed Python owners plus Tasks installer and complete alignment tests (25 files) | 811 passed, one Windows-only drive-relative manifest test skipped. |
| Runtime contract/default selection tests | 84 passed; real runtime discovery confirms optional `tasks.rebind` without raising the installer-wide minimum. |
| Filesystem boundary tests | 68 passed, including all three socket-inode cases; also included in the focused run above. |
| Complete Go module | `go test ./... -count=1` passed. |
| Go static analysis | `go vet ./...` passed. |
| Python source lint | `ruff check src/ --select E4,E7,E9,F` passed. |
| Wheel and installed package | Wheel built; exact packaged context schema and Classic/Advanced recovery references verified; installed CLI help and packaged context tests passed. |
| Changed Markdown | Touched Markdown passed markdownlint; the 27 Markdown files changed by the cumulative feature stack also passed after six narrow formatting repairs. |
| Full repository Markdown | Existing historical documentation and test-fixture violations remain; comparison against the original feature snapshot distinguishes that baseline from the touched files. |

The full Python suite was attempted but interrupted while unrelated init tests
waited on runtime downloads. The focused and runtime-selection counts above are
the completed evidence. Native Windows/macOS execution and the full Python
version matrix still require working cloud runners.

Observed GitHub Actions runs on the original main and feature heads failed
before executing job steps (`runner_id=0`, empty steps, unavailable job logs).
For example, [#120 Test run 35701114808](https://github.com/chenziyang110/spec-kit-plus/actions/runs/35701114808)
and [Lint run 35701114825](https://github.com/chenziyang110/spec-kit-plus/actions/runs/35701114825)
provide no code-execution result. The evidence does not establish an account
billing cause. Final-head Actions status must be checked separately; local
results do not imply cloud CI or release verification passed.
