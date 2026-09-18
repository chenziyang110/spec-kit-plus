# Spec Kit Plus optimization status

Updated: 2026-09-18 (Asia/Tokyo). This local-state I/O increment follows
`a71552cfeff510717062c3385c7170a3c58478ec` on draft PR #120.

## Current decision

Keep dependency order **#116 -> #119 -> #120** and keep the PR draft. No main
merge, release, installed upgrade or generated-consumer switch is implied.
Classic/Advanced defaults, capability minimums and result/review/acceptance gates
remain unchanged. The broader restructuring and measured adaptive rollout from
the original review are not implicitly complete.

Retained work includes bounded context/shadow discovery, strict runtime response
checks, independent executable copies, project writer locks, no silent project
fallback, machine-binding verification and exact-wrapper permission repair.
These are not evidence of real Agent savings, verified live-source/design inputs
or independent human acceptance.

## Latest: regular-file state I/O and lock identity

The shared `atomic_io` readers previously blocked on a POSIX FIFO, while atomic
writes could replace an existing FIFO or filesystem socket with a regular file.
An empty lock hardlinked to another file could initialize that external file.
A waiting process could acquire an obsolete lock inode after its path changed.

State reads now validate both pathname and opened descriptor before reading.
POSIX nonblocking open prevents a swapped FIFO from waiting for a peer; final-
component no-follow is used where available. Locks require a regular unshared
inode and recheck pathname identity after acquisition, before the protected body.
Descriptors are closed on validation, wrapping and body errors. Atomic writers
reject special destinations both before staging and immediately before replace.

Normal missing-file creation, byte/text encoding, file modes, retained locks,
platform lock wait policies and regular-file atomic replacement are preserved.
Regular hardlinked data may still be read or replaced independently; only locks
require a single hardlink. The existing launcher metadata readers inherit the
new rejection without adding a parallel parser or repair path. Recovery guidance
is in [Project launcher recovery](../launcher-recovery.md).

Production changes are confined to `src/specify_cli/atomic_io.py`: four existing
function bodies, three private helpers and one typing import. No public signature,
export list, workflow, generator, dependency or capability requirement changes.

## Verification actually executed

Linux amd64, Python 3.13.5 and Go 1.23.2 for retained small executable fixtures.
Original atomic I/O blob: `4d5bd8bfc22163fb4f4cb8602b0ac768d0b82374`.

| Scope | Actual result |
| --- | --- |
| Same 38 new cases against original I/O owner | 26 failures, 12 passes; no errors/skips |
| New special-file, descriptor and lock cases | 38 passed |
| Original atomic I/O test file, unchanged | 3 passed |
| Retained launcher/configuration/response cases | 112 passed |
| Retained materialization/project resolution | 60 passed, including three legacy test bodies |
| Completed final component groups | 213 passed, zero failures/errors/skips |

The baseline includes desired rejection/error types and new descriptor fault
hooks as well as concrete reproduced defects; it is not 26 independent bugs.
FIFO regressions run in bounded child processes and time out on the original
reader. Real filesystem sockets, hardlinks, a real waiting flock process, and
injected open/wrap/flush/publication failures cover rejection and cleanup. Real
launcher binding/dispatcher metadata reads now return unavailable instead of
hanging on a FIFO. No network, release download or credential access is used.

The full launcher, runtime installer, atomic_io and hook_artifacts modules load.
The bundle-only driver bypasses heavy CLI initialization. Generated launcher
children use a small instrumented CLI and retained native programs are fixtures,
not the product runtime. The 172 retained cases are reruns; three old atomic I/O
cases are newly included in this scoped run but are not new tests. Compilation,
AST/public-surface checks and exact source/preimage hashes accompany the logs.
Repeated reproduction runs do not increase independent coverage.

## Remaining gates and limits

| Gate | Required evidence still missing |
| --- | --- |
| Full Go/SQLite/Work/API/Python | Prepared complete checkout and original full suites |
| Full CLI/init/wheel and installed profiles | Complete initializer and installation/repair acceptance |
| Native Windows/macOS | Actual native execution, not cross-compilation or configured jobs |
| Cloud CI | Successful current-head execution and accessible failure details |
| Live-source/design and Agent quality/cost | Existing owners, comparable real runs and independent acceptance |
| Main/release/distribution | Passing gates and separately authorized publication |

Parent CI jobs failed without execution steps. Their cause is not established;
inspect the new head independently without inferring billing or weakening gates.
Ruff is unavailable locally; no Ruff pass is claimed.

These checks are not a complete hostile-writer defense, atomic check/use,
filesystem-wide deadline or regular-file size bound. Parent-path races, external
edits and changes after observation remain possible. A directory-sync failure
after successful replace still reports an error without undoing that replacement.
Project locks do not serialize all machine-global writes or provide multi-file
rollback. Readers outside the shared state helpers are not changed by this repair.

## Complete-checkout validation

```sh
python -m pytest tests/test_atomic_io.py tests/test_atomic_io_file_types.py
python -m pytest tests/test_launcher_machine_binding_integrity.py tests/test_launcher_config_persistence.py tests/test_runtime_response_integrity.py tests/test_runtime_materialization_isolation.py tests/test_runtime_project_resolution.py
python tools/workflow-quality/verify_quick_rollout.py --output-dir ../quick-rollout-evidence
```

Use a new evidence directory outside the repository. A scoped reproduction bundle
is not a complete checkout or installation package. Preserve user changes and do
not reapply superseded patches. See [CI recovery](../ci-troubleshooting.md) and
[runtime maintenance](../agent-guidance/workflow-maintenance.md).
