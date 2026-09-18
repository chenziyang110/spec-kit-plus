# Spec Kit Plus optimization status

Updated: 2026-09-18 (Asia/Tokyo). This project-runtime resolution increment follows
`eac9f58ce968e396f4085314bb5664cc835af59c` on PR #120.

## Current decision

Keep the dependency order **#116 -> #119 -> #120** and the PR draft. No main
merge, release, installed-project upgrade, permission change or generated
consumer adoption is authorized by these component results.

Implemented work includes explicit Quick execution/output controls; validated
observations and task fixtures; bound context compilation and precise state
reading; optional non-authorizing shadow CLI/discovery; cancellation and output
checks; independent runtime copies; and exit-aware, single-handshake Python
consumption. These implementations do not establish measured Agent savings,
live-source correctness, design approval or independent product acceptance.
Classic/Advanced products, required capabilities and result/review gates remain.

## Latest: project pins cannot silently fall back

The Python consumer now distinguishes a genuinely unbound directory from a
broken project binding. A failed digest/launcher check, malformed config,
orphaned pin, unreadable state or unsafe project path raises
`SpecifyRuntimeBindingError` before environment/PATH selection or automatic
installation. `install_if_missing=True` and `check=False` do not waive this
selection boundary. Explicit bootstrap without a project remains supported.

Subdirectory calls use the nearest `.specify` boundary and its existing validated
launcher owner. Nested projects do not borrow an enclosing project's pin. The
executable becomes absolute while the original command arguments and working
directory stay unchanged. Resolution does not write, repair, install or probe.
The actual config-save-failure path is covered: the mismatched pin blocks calls,
then a deliberate existing-writer repair restores normal project-local execution.
This is still not a filesystem transaction, signature check or atomic check/use.

Current Linux evidence: **32 new parameterized cases and 113 retained cases
passed (145 total), with zero failures/skips**. The same 32 new cases on the
original runtime produced 26 failures and six passes, with no collection errors
or skips. Real native Go fixtures verified the executable path, cwd and argv;
these are small test programs, not the full Specify Go runtime. The complete
launcher/runtime/atomic_io/hook_artifacts modules run, with only heavy package
initialization bypassed by the local driver. All top-level constants/imports
and unrelated runtime definitions were checked unchanged. Only two existing
runtime functions change; one private resolver and one error subtype are added.

The [installation guide](../installation.md) now explains recovery and corrects
its obsolete hardlink description. Complete CLI init, machine binding probes,
wheel/profile installation, full Go/Python suites and native Windows/macOS remain
unverified. Prior cloud failures do not become passes from these local results.

## Retained launcher persistence repair

The original runtime-config writer materialized a new binary before loading the
existing config or resolving binding metadata. Bad configuration or a metadata
exception could leave a changed binary and an old binding. Both Specify and
runtime config writers also performed unlocked whole-object read/modify/write.
Controlled real subprocesses reproduced a second installation modifying the pin
while the first writer was paused just before its config write.

The two writers now share the existing OS lock primitive at
`.specify/runtime/launcher-config.lock`, covering config reread, owned file work
and binding publication. The file is retained (not unlinked on release) and
ignored with the existing runtime-owned state directory. Different projects do
not share a lock. Existing default-launcher no-ops still create no project state.

Existing malformed configuration is rejected before materialization or binding
writes. Config JSON rejects duplicate decoded keys, non-finite values, invalid
UTF-8 and unpaired surrogate escapes; legitimate Unicode, exact integer user
values, existing fields and ordinary JSON-number behavior are retained. Binding
metadata is obtained and checked for JSON representability before replacing the
project binary. Foreign Specify ownership and explicit trusted-source selection
keep the original rules. No credentials are read or release assets downloaded.

## What the lock does not guarantee

This is serialization for the **two cooperating launcher writers**, not a global
init transaction. Readers, low-level binary-copy callers and external editors do
not acquire this lock. A later config-save failure can still leave a new binary
with the old binding; the write raises, and the existing loader rejects the
mismatched pin instead of certifying it. A deliberate subsequent repair can
restore a matching binding. No rollback or crash-atomic multi-file commit is
claimed. A killed process releases its OS lock, not its completed side effects.

Do not delete a lock file to unlock it. The existing platform primitive owns its
wait/release policy; no new timeout or platform-isolation claim is introduced.
Machine-wide local binding dispatchers and complete concurrent `specify init`
remain separate validation work.

## Historical eac9f58 verification

Environment: Linux amd64, Python 3.13.5, Go 1.23.2 (the retained tiny executable
copy fixture). Exact original launcher blob:
`eddbc7bb2ed5e02e4577fc8849125037e8e496e6`.

| Executed scope | Result | Interpretation |
| --- | --- | --- |
| Original-code regressions | 9 expected failures | Six bad-config cases, one metadata failure, two real-process interleavings |
| New launcher persistence cases | 31 passed | Includes parameterization, not 31 new test functions |
| Retained response and materialization cases | 82 passed | Reruns of 54 response and 28 materialization cases |
| Combined selected Python run | 113 passed, zero failures/skips | Component integration, not complete repository verification |
| Python compilation and AST scope checks | Passed | Three existing launcher functions change, one lock helper added; constants preserved |

Real-process tests pause one writer before config publication, observe the
second waiting, then release and check final binary/config agreement and retained
user fields. Other tests cover actual process termination and lock release,
different-project progress, symlink path refusal, both binding loaders, pinned
runtime precedence, idempotence, and explicit config-save failure/recovery.

The complete launcher, runtime installer, atomic_io and hook_artifacts modules
are loaded. Unlike earlier fixtures, launcher imports are no longer replaced.
Only the heavyweight CLI package initializer is bypassed in the local test
driver. Source-bound Specify persistence is exercised without running uvx;
machine-local binding generation/probing and full init are not asserted tested.
The committed tests use normal imports in a prepared complete checkout; the
partial-package driver is delivery evidence only, not production code.

The prior selected Go results remain historical and were not rerun here. Ruff
is unavailable locally; no Ruff, wheel, native Windows/macOS or full CI pass is
claimed. Repeated reproduction runs are not extra independent test coverage.

## Remaining acceptance gates

| Gate | Current state | Required evidence |
| --- | --- | --- |
| Complete Go/SQLite/Work/API and all named cases | Not validated | Complete clean checkout, prepared dependencies, original suites |
| Full Python/init/launcher/wheel and profiles | Not validated | Entire installed consumer path, including machine-local bindings |
| Native Windows/macOS | Not executed here | Actual native execution, not configured jobs or cross-compilation |
| Cloud CI | Prior jobs failed without readable steps | Actual job execution and accessible failure detail; do not infer billing |
| Live source/design input consumption | Not verified by shadow | Existing source/design owners before projection adoption |
| Real Agent quality/cost | Not measured | Comparable runs and independent acceptance |
| Main/release/distribution | Not performed | Passing gates and separately authorized publication |

A complete checkout/dependency environment remains unavailable locally. Broader
restructuring and adaptive rollout from the initial review are not implicitly
finished. Preserve private source and user changes; do not weaken existing gates.

## Resume through the existing validation path

In a prepared complete checkout:

```sh
python -m pytest tests/test_launcher_config_persistence.py tests/test_runtime_response_integrity.py tests/test_runtime_materialization_isolation.py
python tools/workflow-quality/verify_quick_rollout.py --output-dir ../quick-rollout-evidence
```

The evidence directory must be new and outside the repository. A scoped
reproduction bundle is not an installation package or complete checkout.
See [CI recovery](../ci-troubleshooting.md),
[shadow usage](../architecture/quick-shadow-cli.md) and
[runtime maintenance](../agent-guidance/workflow-maintenance.md).
