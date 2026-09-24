# Spec Kit Plus optimization status

Updated: 2026-09-18 (Asia/Tokyo). This Hook installation increment follows
`032d49bcb26cfa9f7b35e44c8b5629e9d9cc7b3b` on draft PR #120.

## Current decision

Keep dependency order **#116 -> #119 -> #120** and the PR draft. No main merge,
release, installed upgrade, permission change or generated-consumer adoption is
implied. Classic/Advanced defaults, capability minimums and result/review/human
acceptance gates remain unchanged. The wider structural/adaptive optimization
request is not implicitly finished.

Retained implementation includes bounded context and optional non-authorizing
shadow discovery, strict runtime responses, independent executable copies,
project writer locks, no silent project-pin fallback, machine-binding checks,
wrapper permission repair, safe state/config reads and single-pass diagnostics.
Those changes do not establish real Agent savings, verified live-source/design
inputs or independent product acceptance.

## Latest: independent shared Hook publication

The shared Hook installer still used `shutil.copy2` directly on live destinations.
Real-file reproductions showed that destination symlinks and hardlinks changed
external files. A directory at an expected filename could also be interpreted as
a copy folder. Source links were followed and special source files skipped.

`install_shared_hook_launcher_assets` now validates the asset/destination paths,
reads source bytes through the existing safe reader and publishes through the
existing atomic byte writer. Destination parents are checked before mkdir or
manifest inspection. Existing final-path user links still follow the explicit
preserve-and-report policy when `preserve_modified=True`; ordinary installs reject
them. Hardlinked data destinations become independent files before metadata is
copied, so external backups keep their bytes, permissions and modification time.

The existing metadata-copy and POSIX executable-bit rules, `include_node`, skip
list, manifest recording and four shipped payloads are retained. Only this one
production function changes; imports, constants, signatures, public commands,
dependencies, shared I/O, script generators and integration registrations do not.

Atomic byte publication is per file. A later metadata or manifest error can leave
new content with a previous manifest digest; it raises instead of certifying
success. Earlier files in the call are not rolled back. See
[shared Hook recovery](../launcher-recovery.md#shared-hook-asset-installation).

## Verification executed in this increment

Linux amd64, Python 3.13.5, Node 22.16.0 and Go 1.23.2 for retained native fixtures.
Original launcher blob: `01fdbdfc002096ac2872586ffa7d9069060cb541`.

| Completed scope | Actual result |
| --- | --- |
| Exact original launcher, same 40 new cases | 17 failures, 23 passes; zero errors/skips |
| New Hook publication and real launcher-chain cases | 40 passed |
| Retained diagnostics/config reads/responses/state I/O | 152 passed |
| Retained machine bindings and config concurrency | 58 passed |
| Retained materialization and project resolution | 60 passed |
| Final total across four completed groups | **310 passed; zero failures/errors/skips** |

The 310 total is 40 new cases plus 270 reruns, not 310 additions. Baseline failures
include new fault hooks and rejection requirements, not 17 independent bugs.
Twenty-eight new cases cover publication, hardlink isolation, path refusal,
preservation, metadata, real manifest save/load, selection and fault injection.
Twelve use the unchanged shipped Python, POSIX shell and Node launcher chains for
Claude/Gemini routes, checking stdin, literal/Unicode arguments, project cwd and
both successful/nonzero exits. Only the final downstream dispatcher is an
instrumented test leaf; no real agent or workflow mutation runs.

The complete production launcher/runtime/atomic_io/hook_artifacts and integration
manifest modules execute. The fetched manifest and four Hook payloads match the
pinned Git blob bytes. The bundle driver omits the heavyweight CLI initializer
and integration registry; its absent registry package uses the manifest module
through the namespace path. This is not full `specify init` or integration/profile
acceptance. Retained native Go programs and generated binding CLIs are fixtures.
The original three legacy materialization test bodies remain included.

Source syntax/public-surface and preimage checks accompany the logs. Rerunning a
group does not increase independent coverage. Tests do not use real credentials,
release downloads or network services. The complete source checkout is not present.

## Remaining gates and limits

| Gate | Evidence still required |
| --- | --- |
| Full Go/SQLite/Work/API/Python | Prepared complete checkout and original full suites |
| CLI/init/wheel and both installed profiles | Complete initialization, install and repair acceptance |
| Native Windows/macOS | Actual execution, not syntax checks or copied script bytes |
| Cloud CI | Successful current-head execution and accessible failure details |
| Live-source/design and Agent cost/quality | Existing owners, comparable runs and independent acceptance |
| Main/release/distribution | Passing gates and separate publication authorization |

Parent CI still reports failures without job steps. The check-run API lists
annotations, but the current connector rejects their endpoint, so the cause is
not established. Inspect the final commit's runs separately; do not infer billing
or weaken checks. Ruff is not installed locally and is not claimed passed.

These local checks do not provide an atomic check/use guarantee, filesystem-wide
deadline, regular-file size bound, signature check or hostile-writer isolation.
Project writer locks do not serialize every integration install, machine-global
update or external editor. No multi-file crash transaction or rollback is claimed.

## Complete-checkout validation

```sh
uv run pytest tests/test_hook_asset_installation.py tests/test_launcher.py -q
uv run pytest tests/integrations -q
python tools/workflow-quality/verify_quick_rollout.py --output-dir ../quick-rollout-evidence
```

Use a new external evidence directory. A scoped reproduction
bundle is not an installation package or a complete repository. Preserve user
changes and do not reapply its patch over a head that already contains it. See
[local development](../local-development.md) and [CI recovery](../ci-troubleshooting.md).
