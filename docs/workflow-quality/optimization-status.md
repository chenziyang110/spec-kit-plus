# Spec Kit Plus optimization status

Updated: 2026-09-18 (Asia/Tokyo). This guidance-diagnostics increment follows
`7894242e821816e8de61e24e8cfa3b6c8c92f5e2` on draft PR #120.

## Current decision

Keep dependency order **#116 -> #119 -> #120** and keep the PR draft. No main
merge, release, installed upgrade or generated-consumer switch is implied.
Classic/Advanced defaults, capability minimums and result/review/acceptance gates
remain unchanged. Broader restructuring and measured adaptive rollout are not
implicitly complete.

Retained work includes bounded context/shadow discovery, strict runtime responses,
independent executable copies, project writer locks, no silent project fallback,
machine-binding checks, wrapper permission repair and regular-file state I/O.
These do not establish real Agent savings, live-source/design approval or human
acceptance.

## Latest: safe, single-pass generated guidance diagnostics

The diagnostic's document/script reader still used ordinary `Path.read_text`.
Invalid UTF-8 aborted diagnosis, fixed-path FIFOs waited for peers, discovery
silently skipped some special paths/access errors, and linked generated roots
could lead the scan outside the project. Two launcher checks rediscovered and
reread the same guidance separately.

The scan now uses the existing safe state reader, reports each uninspected path
as `unreadable-generated-guidance` / `repairable-block`, and continues checking
readable files. Discovery explicitly reports inaccessible or linked directories,
does not descend directory links, includes special-file candidates for rejection,
and sorts/deduplicates the resulting paths. Missing optional assets stay optional;
a discovered file lost before reading is reported. User bytes/modes are not changed.

Both checks reuse derived findings from one discovery/read pass. The cache lasts
only for one invocation and stores findings rather than all document contents;
only repeatedly used fixed helper text is cached. Managed context-block and YAML
frontmatter boundaries and existing diagnostic predicates remain intact.

Current Linux/Python 3.13.5 component evidence: **27 new cases plus 243 retained
cases passed (270 total), zero failures/errors/skips**, across seven completed
non-overlapping groups. The same 27 cases on the exact parent launcher produced
21 failures and six passes, no errors/skips. These are scenario counts, not 21
independent defects. Larger retained invocations hit the tool execution limit;
only separately completed XML/logs are counted. The isolated driver disabled
unrelated installed pytest-plugin autoload for the retained groups, not repository
CI checks. Full package initialization is still bypassed by that delivery driver.

A 64-document fixture counted discovery calls **2 -> 1** and document reads
**128 -> 64**, with identical diagnostic codes. Only executable-compatibility
probes were stubbed in this count fixture; discovery/reads/assembly ran normally.
This measures avoided scan I/O, not installed CLI latency or Agent cost. The new
suite covers real invalid bytes/FIFOs/symlinks, controlled access failures, per-call
refresh, disappeared files, preserved user files and existing content boundaries.

Only `_generated_guidance_files` and `diagnose_project_runtime_compatibility`
change in production. The private discovery helper gains an optional reporting
callback; public signatures, imports, constants and unrelated definitions remain
unchanged. No runtime capabilities, defaults, dependencies or generators change.

## Previous: connect project config to the safe state reader

The launcher's JSON loader still used `Path.exists()` and `Path.read_text()`.
As a result, FIFO project configuration blocked six real loader/diagnostic/writer
entrypoints despite the previous shared-reader fix. Existing and parent links
were followed, while dangling links were treated as absent configuration.

`_load_config` now uses the existing `read_local_state_text` owner. Only a missing
file returns the original unbound `{}` value; unsafe/unreadable paths and invalid
JSON remain `None`. Unique-key, finite-number, strict Unicode and exact integer
handling are retained. The loader does not write, install, retry or add a parser.
Other launcher-owned JSON consumers inherit the same file checks.

Compatibility diagnosis now returns one `invalid-project-config` repairable block
before unrelated scans or launcher probes when the project configuration is
invalid. This avoids misleading missing-runtime recovery advice. Missing or empty
valid configuration still produces the existing unbound-project diagnostics.
Recovery preserves configuration and binary pins; it does not delete bindings or
edit stored digests. See [launcher recovery](../launcher-recovery.md).

Only `_load_config` and `diagnose_project_runtime_compatibility` change in the
production launcher. Imports, constants, public signatures, unrelated functions,
shared I/O implementation, runtime capabilities and generators remain unchanged.

## Historical parent verification

Linux amd64, Python 3.13.5, Go 1.23.2 for retained small native fixtures. The
original launcher matches Git blob `287468d1d9e9e9b170d0897366ce228fa5fbf108`.

| Completed scope | Result |
| --- | --- |
| Same 30 new cases against the original launcher | 14 failures, 16 passes; no errors/skips |
| New config-read/diagnostic cases | 30 passed |
| Retained machine binding/wrapper cases | 27 passed |
| Retained configuration/concurrency cases | 31 passed |
| Retained response and shared state I/O cases | 95 passed |
| Retained materialization/project resolution | 60 passed |
| Final total across completed groups | 243 passed, zero failures/errors/skips |

The baseline includes six actual FIFO timeouts, three link-policy checks and
injected access/probe-order requirements. It is not 14 independent defects.
The 213 retained cases are reruns, not new tests; the file group still contains
three unchanged legacy test bodies. One combined retained-group attempt reached
the tool timeout without a complete report; it is not counted. Its scopes were
subsequently run in separate completed groups above.

Complete production launcher/runtime/atomic_io/hook_artifacts modules execute;
the local driver bypasses heavy CLI package initialization. Generated binding
children and native Go programs remain small fixtures. Tests call the actual
loader, compatibility diagnostic and both public launcher writers, not the full
`specify check` or `specify init` CLI. Regular JSON, Unicode/CRLF/exact integers,
missing state, invalid JSON, links, special files and non-mutating failure paths
are covered. Compilation, AST scope and byte-identity checks accompany the logs.

## Remaining gates

Full Go/SQLite/Work/API/Python suites, complete CLI/init/wheel/profile acceptance,
native Windows/macOS, successful cloud CI, live-source/design verification and
comparable real Agent quality/cost measurements remain open. Main publication
requires passing gates and separate authorization.

The container cannot resolve github.com, so a complete clone was not obtained.
An earlier Go job log request returned 404 BlobNotFound; historical jobs
remain failed and their root cause is unknown. Inspect new-head CI separately. Ruff is not installed locally and is not claimed passed.

These reads are not atomic check/use, signatures, a sandbox, regular-file size
limits or a filesystem-wide timeout. Concurrent changes after observation remain
possible. No new installation transaction or automatic rollback is introduced.

## Complete-checkout validation

```sh
uv run pytest tests/test_launcher_guidance_diagnostics.py tests/test_launcher_config_read_boundary.py -q
uv run pytest tests/test_launcher_machine_binding_integrity.py tests/test_launcher_config_persistence.py tests/test_runtime_response_integrity.py tests/test_atomic_io.py tests/test_atomic_io_file_types.py tests/test_runtime_materialization_isolation.py tests/test_runtime_project_resolution.py -q
python tools/workflow-quality/verify_quick_rollout.py --output-dir ../quick-rollout-evidence
```

Use a prepared complete checkout and a new evidence directory outside it. A
scoped reproduction bundle is not an installation package or complete checkout.
Preserve user changes and do not reapply superseded patches. See
[local development](../local-development.md) and [CI recovery](../ci-troubleshooting.md).
