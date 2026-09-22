# Cumulative integration repair rollout

Updated: 2026-09-22. Source maintenance on draft PR #120, not a release,
main merge, installed upgrade or full product acceptance. Keep dependency order
#116 -> #119 -> #120 and preserve Classic/Advanced contracts.

## Source checkpoints

Commit `50bdd2250dc1776246570b131684241206bb8bdf` landed the previously local
cumulative atomic I/O and manifest owners over `7b2233e`, plus the manifest and
lock-test adaptations, primary-error tests and this rollout record. Exact blobs:

- atomic_io.py at that checkpoint: `a617edd0e85d52317f3db7da35588a5106a3b56a`
- integrations/manifest.py: `b05881f1c7811195279f9721f4b4e022a2a0b6a6`

Those changes include independent file publication; strict metadata persistence
and opaque extension preservation; revision checks for save/write/cleanup;
shared-asset retention; recoverable failed uninstall; streamed hashes; finite
lock waits; umask-respecting creation; idempotent save with correct retry markers;
long staging names; and preservation of primary write errors.

## Follow-up: preserve protected failures during unlock

A failing explicit unlock used to mask errors raised by protected work, including
ENOSPC, KeyboardInterrupt and SystemExit. interprocess_lock now keeps the original
error and adds the release failure as an exception note. When protected work
succeeded, a release error still propagates. Descriptor closure remains owned by
the existing checked file opener; the coordination path is never removed.

Only interprocess_lock changes in this follow-up. Public arguments, imports and
other production files remain unchanged. New atomic_io blob:
`28a5a51c99f79c513bbf03ebf7acd2b71db228f4`.

## Verification actually executed

The exact first checkpoint's original manifest suite, file-type suite and new
primary-error suite completed with **90 passed, 1 Windows-only skip**. Its
unchanged parent launcher blob was `dc369f55a54beac90c7edd5846221b17d7a3e3b7`.

The follow-up adds ten real POSIX lock/descriptor tests, including a child that
receives actual SIGINT. The same tests on the first checkpoint produced eight
failures and two passes. The updated exact component combination completed with
**100 passed, 1 Windows-only skip**, zero failures/errors. Original exception
identity, errno, cause, traceback, notes, file state and later lock acquisition
are checked. Explicit unlock errors are injected; this is not a native Windows
or arbitrary descriptor-close-failure guarantee.

Complete component modules execute, but root CLI and integration registry
initialization are omitted in the scoped tree. This is not full repository or
installed acceptance. Earlier broader local-suite totals are historical evidence,
not a claim that every local test has been transferred or rerun in these commits.

## Current CI observation

For `50bdd22`, Test & Lint run `35699529355` and Lint run `35699529430` report
failure. The seven test jobs have no returned steps or log URL. Fetching the
Python 3.13 job log returned 404 BlobNotFound. Root cause is not established;
these responses do not prove product tests ran. No checks were disabled.

## Remaining transfer and acceptance

The cumulative launcher guard, full integration-base changes, additional
regression files, consolidated recovery documentation and delivery tools still
need separate verified transfer. Do not describe these checkpoints as all local
work being pushed. Never replace base.py with partial source-slice fixtures.

Full package initialization, integration profiles, CLI install/repair/uninstall,
wheel packaging, whole-repository Python/Go suites, native Windows/macOS and
successful current-head CI remain separate gates. Per-file replacement and
revision observations do not provide whole-install transactions or rollback.
