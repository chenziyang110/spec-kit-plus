# Cumulative integration repair rollout

Updated: 2026-09-22. This is source maintenance on draft PR #120, not a release,
main merge, installed upgrade or full product acceptance. Keep dependency order
#116 -> #119 -> #120 and preserve Classic/Advanced contracts.

## First source checkpoint

The previously local cumulative `atomic_io.py` and `integrations/manifest.py`
changes are now included in this commit, over `7b2233e`. Their Git blobs match
the delivered `primary-errors` component bundle exactly:

- atomic_io.py: `a617edd0e85d52317f3db7da35588a5106a3b56a`
- integrations/manifest.py: `b05881f1c7811195279f9721f4b4e022a2a0b6a6`

This includes safe independent file publication; metadata persistence and opaque
extension preservation; per-integration revision checks for save/write/cleanup;
shared-asset retention; recoverable failed uninstall; streamed hash comparison;
finite lock acquisition; umask-respecting creation; idempotent save with correct
retry markers; long staging names; and preservation of primary write errors.

The original manifest retry tests now inject errors at atomic replacement rather
than truncating the live file. The existing lock waiter test recognizes the
nonblocking lock flag. Their original assertions are retained. The primary-error
regressions are included as a new test file.

## Validation of this checkpoint

An isolated component tree used these exact files and the unchanged parent
launcher (`dc369f55a54beac90c7edd5846221b17d7a3e3b7`). Running the original manifest
suite, shared file-type suite and new primary-error suite completed with
**90 passed, 1 Windows-only skip**, zero failures/errors. The complete component
modules execute, but the heavyweight root CLI and integration registry are not
present in this scoped tree. This is not full repository or installed acceptance.
The previously delivered broader local suite is historical evidence, not a claim
that all of its tests are present or freshly executed in this commit.

## Remaining source transfer and acceptance

The cumulative launcher guard, full integration-base changes, additional
regression files, consolidated recovery documentation and delivery tools still
need separate verified transfer. Do not describe this checkpoint as all local
work being pushed. Never replace base.py with the partial source-slice fixtures.

Full package initialization, integration profiles, CLI install/repair/uninstall,
wheel packaging, whole-repository Python/Go suites, native Windows/macOS and
successful current-head CI remain separate gates. Per-file replacement and
revision observations do not provide whole-install transactions or rollback.
