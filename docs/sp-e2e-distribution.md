# E2E installation and wheel verification

Scenario design, visual execution and native runner evidence are separate from
whether `sp-e2e` can actually be installed. The distribution gate tests that
last boundary without replacing the existing full Python/Go, desktop or lint
checks. It does not publish a release or change required branch protections.

## Repository installation tests

`tests/integrations/test_e2e_installation.py` retains all 44 cases: 38 native
rendering combinations and six real init/additive-upgrade cases. The six init
cases now consume the existing `unified_runtime_env` fixture from
`tests/conftest.py`. That fixture builds the current Go runtime and sets an
explicit test-local bootstrap override. This avoids allowing an old cached or
network-downloaded release to stand in for the changed source. No installer,
renderer, preservation assertion or required check is mocked out.

Run with the repository's declared Python/Go toolchains:

```sh
if [ -e uv.lock ] || [ -L uv.lock ]; then
  uv lock --check
else
  uv lock
fi
uv sync --frozen --extra test
uv run --frozen --extra test pytest tests/integrations/test_e2e_installation.py \
  tests/test_e2e_registration.py tests/test_e2e_wheel_verifier.py \
  tests/test_e2e_wheel_snapshot.py tests/test_e2e_distribution_lock.py
```

## Archive verification

`tools/workflow-quality/verify_e2e_wheel.py` compares the built wheel with the
actual source bytes for the four E2E helpers, Classic command and shared
partials, independent Advanced E2E skill and reference, Advanced shared assets,
workflow registry and Python entrypoint. Every selected archive member must
also have the matching SHA-256 and size in wheel `RECORD`. Missing source trees,
missing members, duplicate archive/RECORD entries and mismatched bytes fail.
The checker is read-only, does not extract ZIP members and emits no installed
or executed-product claim. Its checks remain enabled under Python `-O`.

```sh
uv build --wheel --out-dir /tmp/e2e-wheel-dist
uv run --frozen --extra test python tools/workflow-quality/verify_e2e_wheel.py \
  --wheel /tmp/e2e-wheel-dist/<built-wheel>.whl --source-root .
```

## Actual installed-wheel probe

The independent probe is `tests/e2e_samples/wheel_install_probe.py`. Execute it
with the Python interpreter of a fresh virtualenv that has the built wheel and
its dependencies installed, using `-I`. Do not run it with `uv run`: that may
select the editable source environment rather than the wheel environment.

It refuses source/editable imports, compares installed E2E assets to the wheel,
and then performs real CLI subprocess calls in four new disposable projects:
Classic then Advanced and Advanced then Classic, each with `sh` and `ps` asset
generation. Generating PowerShell assets on Linux is not native PowerShell
execution; native-platform jobs are separate matrix entries.

For each project the probe verifies first-profile isolation, both E2E skills,
Advanced references, implicit-invocation policy, all four shared helpers and
core/agent manifests. It edits a managed skill and helper deliberately, adds the
second profile, then verifies both user edits survive. It deletes only the
second, unmodified E2E skill in that disposable project and invokes the real
`specify integration repair`, checking restoration and preservation again.

The supplied source-built runtime must be copied byte-for-byte into the
project-local launcher path, report the expected source revision and recognize
`learning start --command sp-e2e`. The helper catalog and native-runner help are
executed from their installed paths, not inferred from archive membership.
The runner's help uses `-E -s` rather than `-I` because its documented standalone
script layout imports its sibling coverage helper. The wheel import probe uses
`-I`; CLI calls use the fresh virtualenv's actual console entrypoint with source
Python paths removed and test-local runtime/cache bindings.

Example after creating and populating the wheel-only virtualenv:

```sh
/path/to/wheel-venv/bin/python -I tests/e2e_samples/wheel_install_probe.py \
  --wheel /tmp/e2e-wheel-dist/<built-wheel>.whl \
  --runtime /tmp/specify-runtime \
  --expected-revision "$(git rev-parse HEAD)" \
  --expected-wheel-sha256 "<wheel_sha256 from wheel-assets.json>" \
  --output /tmp/e2e-wheel-run-001
```

Use the platform-native virtualenv interpreter and runtime filenames on Windows.
The output must be new and outside the source checkout. The probe never
installs software itself, never deletes user project files and never overwrites
previous evidence. It preserves actual child argv, stdout, stderr and exit
codes in `commands.json` and separate logs. Only a successful whole probe writes
`result.json`; failures retain `error.json` and whatever diagnostics exist.
The test-local dirty-build allowance follows the existing runtime test fixture;
it does not authorize publishing a dirty or mismatched runtime.

## Input identity across verification stages

The archive verifier keeps one regular-file descriptor open throughout member
validation. It hashes that descriptor in bounded chunks before and after the
ZIP reads and rechecks both descriptor metadata and the current named file.
It also re-enumerates the selected source assets before returning, so edits,
removals and newly added references during validation invalidate the result.
The reported wheel digest comes from the checked descriptor, never a new
pathname read after the archive has closed.

Pass `--expected-wheel-sha256` from the source/archive report into the installed
probe. CI supplies this binding explicitly. Standalone callers may omit it for
compatibility, but then establish only a probe-local wheel binding, not continuity
with an earlier archive report. In either mode the probe freezes the wheel hash,
checks the original installed asset bytes before and after all project operations,
and reports the original hash only when the checks succeed. A wheel replaced
between archive verification and the probe fails before any project is initialized.
These are observed stability checks, not an atomic snapshot or protection against
a hostile process deliberately coordinating undetectable changes. Use isolated
build directories and do not rewrite inputs during verification.

The snapshot repair reproduced two false-success cases in the previous verifier:
replacement of the wheel after ZIP reads, and a source edit after inventory.
Both now fail closed. The original 29 verifier/probe-guard tests are unchanged;
24 new snapshot, binding and CLI checks bring the focused local run to 53 passes,
zero skips on Linux/Python 3.13.5/pytest 9.0.2. Archive/source payloads remain
explicitly synthetic; the tests synchronize actual temporary-file mutations.
This is not a completed Specify wheel installation or native-platform CI pass.

## Dependency lock preparation and continuity

The inspected source revision has no committed `uv.lock`. Running
`uv sync --frozen` directly from that checkout fails before the installation
suite can start. The distribution workflow now explicitly resolves a missing
lock once for its job. When a lock already exists, `uv lock --check` must succeed;
a stale or malformed lock fails rather than being silently regenerated.

The job snapshots the resulting lock with create-only writes and records its
SHA-256, the `pyproject.toml` hash, checkout revision and whether it validated an
existing lock or resolved one for this run. Sync, project `uv run` commands and
export then use `--frozen`; test commands also explicitly retain `--extra test`.
After the actual wheel probe, a separate guard compares the current lock,
snapshot, hashes and source revision before the job can succeed. The private
run artifact retains `uv.lock` and `dependency-lock.json` beside earlier evidence.
This does not remove or weaken installation, catalog, no-skip or wheel gates.

A generated lock is per-job evidence, not a newly committed repository lock.
Different matrix jobs or later runs may resolve different versions when no
repository lock is supplied; compare their recorded digests rather than claiming
one identical dependency matrix. Build-backend isolation and the external package
index are not made hermetic by this check. Resolution/network failures remain
real failures, not reasons to use fabricated versions or skip validation.

`tests/test_e2e_distribution_lock.py` executes the actual workflow shell blocks
with real uv in dependency-free, offline temporary projects, including paths with
spaces. Its 13 local checks passed with zero skips on Linux/Python 3.13.5,
pytest 9.0.2 and uv 0.10.0. They cover missing/valid/stale/malformed locks, real
frozen sync/run/export, previous-evidence preservation and post-run input drift.
No Specify dependencies or wheel are installed by these fixture tests. They prove
the lock precondition and recovery path, not a full installation or cloud CI pass.
The missing-lock defect is independently reproduced; it does not establish the
cause of earlier cloud jobs whose steps and logs could not be retrieved.

Lock creation and checks follow the official
[uv locking and syncing contract](https://docs.astral.sh/uv/concepts/projects/sync/).

## CI and evidence boundaries

`.github/workflows/e2e-distribution.yml` runs the source tests, wheel build,
archive check, locked dependency installation and isolated wheel probe on Linux
with Python 3.11/3.12/3.13, plus Windows and macOS with Python 3.13. Every case
uses the Go version declared by `go.mod`; no public runtime release is needed.
Artifacts contain the source revision, dependency lock and binding, JUnit results, wheel hash/asset report,
actual process logs and success/failure report. They do not upload disposable
project trees, credentials, source archives or publishable releases.

At authoring, 29 verifier/probe-guard regression tests passed locally on Linux,
Python 3.13.5 / pytest 9.0.2, zero skipped. Their wheels and source trees are
explicitly synthetic fixtures. This is validation of the packaging checker and
failure/isolation boundaries, **not** a completed real wheel installation.
Those installation and wheel gaps describe the initial authoring environment.
The 2026-09-30 complete Windows checkout subsequently passed all 44 installation
checks and the registration/affected-owner suites. See the scoped evidence and
remaining matrix boundaries in [E2E readiness](../plans/sp-e2e-readiness.md).
Do not relabel a newly written CI workflow or a failed CI job as verification.
Current GitHub annotations confirm jobs were not started because of account
payment/spending-limit restrictions; no cloud CI pass is claimed.

The actual Windows wheel probe subsequently completed on source revision
`fca0eec980956e394d49a1073f203e10f2b3a6b5`, Python 3.13.11, in a fresh environment
containing the wheel and locked production dependencies, with isolated imports.
Archive/source/RECORD verification covered 83 selected E2E assets and supplied
the wheel digest to the probe. All four Codex installation orders passed:
Classic then Advanced and Advanced then Classic, each with sh and ps generation.
The probe verified native hints, manifests, profile coexistence, preserved user
edits, missing-entrypoint repair, the matching pinned runtime revision, E2E
Learning identity and copied helper execution. It returned
`installed_e2e_wheel_verified` and retained all 72 command logs.

Wheel SHA-256 is
`461c46d8b8bf7ace7e0e2a32868339beff475f08a1bd1bf0dc05c68a1687645c`.
An intentionally edited helper correctly produces `PARTIAL` with that exact
preservation boundary and no remaining diagnostics. This verifies installation
and repair on that Windows environment; generated sh/ps files are not native
shell execution, GUI perception, a complete cross-platform matrix, a public
runtime release or downstream product acceptance.

The isolated Python invocation follows the official
[Python command-line contract](https://docs.python.org/3/using/cmdline.html#cmdoption-I).
Build/install commands follow the official
[uv packaging guide](https://docs.astral.sh/uv/guides/package/) and
[environment guide](https://docs.astral.sh/uv/pip/environments/).
