# CI evidence and recovery

## Distinguish execution from configuration

A workflow file, supplied test, successful test collector or local unit run is
not a full CI pass. Evidence must identify repository, branch, tested commit,
run and attempt, runner, actual test results and remaining skipped coverage.
A green artifact upload is not evidence that the preceding product tests passed.

`test.yml` preserves the original `ruff`, Python-version and `go` check surfaces.
It also configures additive native Windows/macOS runtime and real installer
checks. Matrix fail-fast is disabled so one failure does not cancel independent
diagnostic evidence. Bash pipefail preserves test failures through `tee`.
JUnit/Go JSON reports and source identities are retained in private run artifacts.
New native coverage is configured, not verified until those jobs execute.

## When jobs contain no steps

1. Open the exact run and job in Actions and inspect its annotation/banner.
2. Check Actions availability and the account's billing/spending-limit status
   only when the annotation points there. Do not infer a billing cause merely
   from an empty step list or runner ID zero.
3. If a payment, spending or organization-policy change is required, the account
   owner must authorize and perform it. Never weaken CI, expose private source,
   change repository visibility or replace publication credentials as a shortcut.
4. After the confirmed cause is resolved, rerun the failed jobs once and inspect
   actual step logs plus test reports bound to the exact commit.

If no annotation or log is accessible, report that boundary and keep the cause
unknown. A job-log 404 does not identify why the job failed. Do not repeatedly
rerun an unstarted job without new evidence.

## Local verification is a separate path

Use a clean complete checkout and the environment from
[Local Development](local-development.md). The existing rollout verifier is:

```bash
python tools/workflow-quality/verify_quick_rollout.py --output-dir ../quick-rollout-evidence
```

It requires preinstalled/cached prerequisites and a new output directory outside
the checkout. A blocked preflight is not a product test failure or pass. Partial
source fixtures may validate their isolated modules but must not be presented
as a complete runtime, installation, operating-system or actual Agent evaluation.

Keep source private. Merge/release and anonymous consumer verification remain
separate from local tests and CI; follow the existing release checklist.

## Verify that the required tests actually ran

The existing rollout verifier now emits `quick-rollout-verification-v2` and
requires the thirteen registered shadow entrypoint/state cases, the existing
Quick lifecycle cases and core context checks. It inventories packages with
host-applicable Go test files before execution, then requires every inventoried
package to pass. Every package/test observed in the event stream must terminate.
A truncated log, skipped required case, duplicate JSON key or missing package
cannot be a passing result. Optional platform-test skips remain visible counts;
they do not replace required cases or another platform's native execution.

The Linux and Windows/macOS jobs use this same checker after `go test ./...`.
Their artifacts retain `test-source.txt`, the original Go JSON log, the host's
`go-test-packages.txt` inventory and `go-evidence-audit.json`. The test command's
exit status and the evidence audit are separate required steps; neither ignores
errors. A supplied workflow is still not evidence that a runner started.

To inspect existing artifacts without running or modifying the project:

```bash
python tools/workflow-quality/verify_quick_rollout.py --inspect-go-log go-test-results.jsonl --go-packages go-test-packages.txt --module github.com/chenziyang110/spec-kit-plus/tools/specify-runtime
```

This read-only mode returns 0 only for complete required Go evidence and 1 for
invalid/missing evidence. It emits `quick-go-evidence-v1`, explicitly says it did
not execute tests, and never authorizes a release. It is not a full-checkout,
Python/install, native-host or source-authenticity attestation. Preserve the
source/run metadata alongside both inputs; a manually altered log and inventory
are not independently authenticated by an offline parser.

Full local validation still uses the original `--output-dir` invocation above
in a clean, prepared checkout. Git inspection and child commands isolate ambient
`GIT_*` overrides so a foreign Git directory cannot silently replace its source
identity. This changes neither repository settings nor any user credentials.

## Runtime watchdog delivery and cancellation

The runtime process wrapper treats output delivery as part of command success.
A failed or short stdout/stderr write returns exit 1, even if the command itself
returned 0. Nonempty diagnostics are delivered before command stdout. Empty
streams are not written. Partial writes are never retried, and no command is
rerun merely because its result could not be delivered. Existing complete
outputs and command exit codes remain unchanged when delivery succeeds.

A result selected at or after its context deadline is not published as success.
The wrapper rechecks the deadline before delivery, after diagnostics and after
stdout. If stdout has already started, a late deadline returns exit 1 without
appending a second JSON response. Synchronous external writer calls cannot be
force-interrupted, and bytes already delivered cannot be retracted.

A timeout before command stdout is published retains exit 10, status `blocked`,
summary `runtime command timed out` and the original operation/timeout fields.
It additionally reports `cancellation_requested`, `command_returned`,
`cleanup_grace_seconds`, `command_stdout_discarded` and `side_effects_unknown`.
`command_returned` means only that the command function's return was observed;
it does not establish that every child process exited. A false value means
that return was not observed within the cleanup grace. The watchdog requests
cancellation but does not roll back completed file changes. It emits no automatic
retry action. Inspect the existing runtime-owned state before retrying a mutation.

These guarantees cover the process watchdog. They do not turn direct library
calls to `Run`/`RunContext` into watchdog-protected process invocations. A failed
output destination can also truncate a timeout envelope; that is exit 1, not a
successful blocked-response delivery. The query/command timeout defaults and
configured maximum are unchanged.
