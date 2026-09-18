# Spec Kit Plus optimization status

Updated: 2026-09-18 (Asia/Tokyo). This increment follows
`a6519ff6cd61f86654fd8ae3cc7d70c1b498cb7d` in PR #120 and includes the previously
local machine-binding repair plus the project-wrapper permission repair.

## Current decision

Keep dependency order **#116 -> #119 -> #120** and keep the PR draft. No main
merge, release, installed upgrade or generated-consumer switch is implied.
Classic/Advanced defaults, capability minimums and result/review/acceptance gates
remain unchanged. The broader restructuring and measured adaptive rollout from
the original review are not implicitly complete.

Retained implementation includes Quick execution/output controls, evaluation
fixtures, bound context and strict state reads, optional non-authorizing shadow
discovery, cancellation/output checks, independent runtime copies, single-handshake
Python validation, cooperating launcher-writer locks and project-pin resolution
without silent fallback. These are not evidence of real Agent savings, verified
live-source/design inputs or independent human acceptance.

## Latest repair

Machine-binding probes require the selected binding's interpreter, not the last
writer's interpreter embedded in a shared repair hint. Entry, invoke and dispatch
scripts must match generated content and hashes; updating the invoke hash and
printing the expected identity cannot substitute for the verified entry. The
same script bytes are hashed and compared. Owned-script links, malformed bytes,
invalid recorded paths and invalid child responses fail the probe. Virtual-
environment interpreter symlinks remain supported.

On POSIX hosts, an exact project wrapper without execution permission is no
longer reported available. Normal repair republishes only identical generated
content as an independent file and restores the existing executable mode. User-
modified wrappers retain conflict/preserve behavior, hardlinked external backups
retain bytes/mode/mtime, and replacement-write errors are reported.

Only three existing production functions change: `_machine_binding_probe`,
`project_specify_launcher_is_available` and `install_project_specify_launcher`,
plus one existing safe-read import. Script generators, commands, dependencies,
capability requirements and workflow defaults are unchanged. Operator recovery
is consolidated in [Project launcher recovery](../launcher-recovery.md).

## Verification executed in this increment

Linux amd64, Python 3.13.5, Go 1.23.2 for the retained small native fixtures.
The original launcher matches Git blob `f488d07c7d4030c71463cdba353bc7992484a4f4`.

| Scope | Actual result |
| --- | --- |
| Original remote code, 20 binding cases | 8 expected failures, 12 passes, no errors/skips |
| Previous local patch, 7 wrapper cases | 4 expected failures, 3 passes, no errors/skips |
| Final binding and wrapper cases | 27 passed |
| Configuration/concurrency regressions | 31 passed |
| Response/handshake regressions | 54 passed |
| Materialization and project resolution | 60 passed, including three legacy test bodies |
| Final total across four completed groups | 172 passed, zero failures/errors/skips |

The 172 cases comprise seven wrapper additions, 20 carried-forward local binding
cases and 145 retained cases. Repeated runs are not additional independent tests.
The full launcher, runtime installer, atomic_io and hook_artifacts modules load.
The local driver bypasses only heavy CLI package initialization. Generated binding
children use a small instrumented CLI with production launcher/IO owners; the
canonical POSIX project template is unchanged and blob-checked. Public writer,
binding generation/probe, config loader, wrapper execution from a nested directory,
Unicode/space/literal arguments and failure recovery are exercised. This is
component integration, not full CLI initialization or a production Go release.

## Remaining gates

| Gate | Required evidence still missing |
| --- | --- |
| Full Go/SQLite/Work/API/Python | Prepared complete checkout and original full suites |
| Full CLI/init/wheel and installed profiles | Complete initializer and installation/repair acceptance |
| Native Windows/macOS | Actual native execution, not cross-compilation or configured jobs |
| Cloud CI | Successful current-head execution and accessible failure details |
| Live-source/design and Agent quality/cost | Existing owners, comparable real runs and independent acceptance |
| Main/release/distribution | Passing gates and separately authorized publication |

At the parent revision, checks remain failed. The Go check reports two failure
annotations, but the available connector rejects the annotation endpoint; the
root cause is not established. Do not infer billing, disable checks, repeatedly
rerun jobs or change permissions based on missing logs. Inspect the new head's
actual results separately. Ruff is unavailable locally; no Ruff pass is claimed.

Project locks do not serialize every machine-global binding write. Access checks
are not atomic check/use; no executable signing, hostile-writer isolation,
multi-file crash transaction or rollback is claimed.

## Complete-checkout validation

```sh
python -m pytest tests/test_launcher_machine_binding_integrity.py tests/test_launcher_config_persistence.py tests/test_runtime_response_integrity.py tests/test_runtime_materialization_isolation.py tests/test_runtime_project_resolution.py
python tools/workflow-quality/verify_quick_rollout.py --output-dir ../quick-rollout-evidence
```

Use a new evidence directory outside the repository. A scoped reproduction bundle
is not a complete checkout or installation package. Preserve user changes; do not
apply the older local machine-binding patch over this increment. See
[CI recovery](../ci-troubleshooting.md) and
[runtime maintenance](../agent-guidance/workflow-maintenance.md).
