# Quick shadow core delivery — 2026-09-17

## What this commit lands

Parent source: 55d2bbc34a17a0f08dddfdcc3f8c86d62a59df35, PR #120.
The two earlier local CLI patch archives were not branch commits. This increment
lands a backward-compatible subset as actual source, not another substitute
public command or execution workflow. Eight Go files and two documents are in
scope. Only quick_context_shadow.go replaces an existing file; all other paths
are additions. Main, releases, installed profiles and public command discovery
remain unchanged.

Seven code files come from the reviewed local v2 package; adapter/handler comments
are corrected to state the unregistered boundary. Five new regular-reader tests
cover exact UTF-8/CRLF bytes, the inclusive 128 KiB limit, pre-cancelled/nil context,
missing and directory inputs, traversal, and symlink/ancestor alias rejection.

See [command core](../architecture/quick-shadow-command-core.md) for ownership.

## Verification executed in this increment

Linux amd64, Go 1.23.2, Git 2.47.3. The container could not resolve external hosts
and no complete source checkout was available. This is selected-source validation.
It is not a full runtime/SQLite/Work, native Windows/macOS or installed-agent run.

- The prior v2 archive patch and eight new files matched their SHA-256 manifest.
- The reconstructed original quick_context_shadow.go matched Git blob
  26884a7b78c411fb30cdd5b5e260a078c537de98 before replacement.
- Unchanged project_path.go matched Git blob
  35f3b162fbce48785392cb68579fbe6e734d8969; Envelope used its original source bytes.
- The prior 22 command/Git/cancellation tests were rerun before any changes.
- The final selected-source suite passed 27 regular top-level tests (77 passing
  events including subtests), zero failures/skips, with race detection enabled.
  This includes those 22 reruns plus five new byte-reader tests; it is not 27
  independent new tests.
- go vet passed for the same selected-source suite. All eight changed Go files
  passed gofmt syntax/format checks.
- The selected fixture uses exact committed core/Git files plus exact function
  bodies extracted from the production state reader and the unchanged path owner.
  It does not provide a substitute Quick state machine. The full adapter/handler
  and public Run/RunContext entrypoint were NOT executed in this increment.

The existing core tests include real child cancellation after observing startup,
parent deadlines, output flooding, malformed identities, raw JSON error handling,
full encoded-envelope limits, and a real local Git repository with ambient Git
identity overrides. Filesystem tests use real temporary files and symlinks.

## Remaining delivery gates

1. Complete the coherent public routing/capability registration and execute its
   eight formal entrypoint tests in a complete checkout. The helper names landed
   here do not mean the CLI command has been registered.
2. Run complete Go/Python, wheel/install, Classic/Advanced and native-OS regressions.
3. Bind real artifact and registered design inputs before switching consumers.
4. Obtain usable cloud CI evidence, then separately authorize main merge/release.
5. Collect real Agent usage and independent acceptance before cost/quality claims.

The old CI failures with empty returned steps do not prove a specific root cause.
Check the new head's actual run separately. No checks are removed or relaxed, no
permissions/source visibility are changed, and no billing cause is inferred.

Older cumulative v1/v2 archives target the parent source and must not be applied
blindly on this commit. A remaining-registration-only patch is a separate local
artifact; its existence is not a passing integration test or a branch change.
