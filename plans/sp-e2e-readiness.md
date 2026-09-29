# SP E2E implementation readiness

## Implemented in this branch

- Independent Classic and Advanced E2E workflow source templates.
- Shared deterministic constrained t-way planner and source/evidence-bound audit.
- Behavioral helper tests and explicit machine/input/output documentation.
- Test-only ownership and preservation of Test Design, Review, and Accept boundaries.
- Native execution wrapper for serial pytest and a local Playwright Test command.
- Exact pre-run bindings, real collection/attempt reconciliation, unique run
  directories, before/after source and test fingerprints, timeout termination,
  and native evidence retained alongside the deterministic coverage audit.
- A real disposable CLI/SQLite sample-application test and adapter regressions;
  usage and limitations are documented in `docs/sp-e2e-runner.md`.

## Verification performed

The original isolated suites ran locally on Linux with Python 3.13.5 and pytest
9.0.2: 57 helper tests and 4 workflow-source contract tests passed (61 total).
That evidence belongs to the initial implementation; it is not a full-repository
run or a claim that later revisions were tested by those original commands.

The continuation independently ran all 48 new `tests/test_e2e_runner.py` tests
on Linux/Python 3.13.5/pytest 9.0.2, in two bounded batches (9 and 39 tests).
The imported coverage helper matched the original Git blob
`f7dc22dd02bd6a94141a0b5e3c294cb2fe58164a`. Real subprocesses exercised a disposable
CLI application backed by SQLite; successful role/amount combinations,
filtering, skips, xfail/xpass, teardown failure, test/source drift, disabled
reporting, collection-only, and timeout were checked. Playwright-specific cases
are parser fixtures, not browser-run evidence. The wrapper is not attestation
that a runner or assertion is truthful.

Python 3.11/3.12, native Windows/macOS, installed-profile validation, packaged
wheel behavior, full source-repository Python/Go suites, and cloud CI were not
verified in this continuation. Do not sum isolated test counts and relabel them
as product E2E or release readiness.

## Still required before merge

1. Register `e2e` in the shared cognition closeout policy and matching Go owner;
   audit Learning, workflow-name validation, reserved extension names,
   orchestration, and agent argument-hint consumers. Preserve the existing
   Work Board route rather than adding an unsupported Activity enum.
2. Add `spx-e2e` to the Advanced surface map and the explicit expected catalog in
   `tests/test_spx_skill.py`; synchronize profile counts/guidance, README,
   PROJECT-HANDBOOK, and init Start Here. Adding the source directory alone is
   not enough: the current hardcoded expected SPX set does not contain it.
3. Verify the installed helpers in isolated Classic and Advanced projects,
   command/skill rendering on supported integrations, exact sidecars/manifests,
   dual-profile coexistence, hooks, and packaged wheel contents. The existing
   `scripts/shared` force-include is not proof of installed availability.
4. Run an actual browser application with the Playwright adapter and verify
   cleanup/global failures, native report version compatibility, and supported
   environments. Native pytest/Playwright execution adapters and the real CLI
   sample now exist; distributed pytest/shard merging are explicitly not
   supported rather than silently claimed complete.
5. Run affected source contract, integration, packaging, and Go suites, review
   the final diff, and require genuine CI evidence. Source commits on this
   branch do not authorize a release or changes to repository visibility.

Keep the PR draft until these gates are closed. Do not remove existing tests,
weaken catalog checks, or present the local helper test count as end-to-end
product readiness.
