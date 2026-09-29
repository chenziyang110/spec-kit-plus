# Native E2E execution and report binding

`e2e_runner.py` executes an explicitly selected local runner, keeps its native
report, checks collection/attempt evidence against the frozen case bindings,
and invokes the existing `e2e_coverage.py` audit. It does not install a runner,
write workflow state, repair production behavior, or grant acceptance.

The source-checkout commands below work from the project root. Generated
projects use `.specify/scripts/shared/` instead of `scripts/shared/` once the
installation/readiness gates have been verified. See
[implementation readiness](../plans/sp-e2e-readiness.md) for outstanding gates.

## Freeze the mapping before execution

First generate a plan from the coverage manifest using `e2e_coverage.py plan`.
Implement the generated cases in the actual E2E harness; put exactly one full
`E2E-` case ID in each native test selector. Keep requirement assertions in the
test, not just the manifest. Review these assertions independently.

Create a bindings JSON file with this structure (replace the illustrative ID
and hashes with the generated ID and SHA-256 of the real UTF-8/file bytes):

```json
{
  "schema_version": 1,
  "manifest_sha256": "<planner manifest_sha256>",
  "test_sources": [{"path": "tests/e2e/test_orders.py", "sha256": "<file sha256>"}],
  "cases": [{
    "id": "E2E-0123456789abcdef01234567",
    "test_ref": "tests/e2e/test_orders.py",
    "selector": "tests/e2e/test_orders.py::test_checkout[E2E-0123456789abcdef01234567]",
    "asserted_requirements": ["R-ORDERS-001"]
  }]
}
```

Bindings must contain exactly the full planned case set, not only selected or
passing cases. Each `test_ref` must be in the hashed `test_sources`. Include all
selected test fixtures, imported helpers, configuration, and data files that
define execution in `test_sources`; the tool cannot discover omitted files.
All file records use normalized project-relative POSIX paths on every OS.
`asserted_requirements` must exactly match the planned case; this checks the
mapping, not whether an assertion is semantically adequate.

For Playwright, `selector` is the exact test title (including its E2E ID),
`test_ref` is the file path relative to the project root, and `project` is the
exact Playwright `projectName`, including the empty string for an unnamed
project. Give browser/project combinations distinct planned IDs and selectors;
do not collapse several projects under one case ID. pytest uses the full
`nodeid`, and `project` is absent or empty.

## Execute the supported runner

For Python E2E tests, the wrapper launches the same Python interpreter with
`-m pytest` and its explicit phase reporter. Other pytest arguments follow `--`.

```sh
python scripts/shared/e2e_runner.py tests/e2e/coverage-manifest.json \
  --bindings tests/e2e/bindings.json --root . --runner pytest \
  --target local-test-build --output-dir test-results/e2e/run-001 \
  --timeout 300 -- tests/e2e -q
```

For Playwright Test, pass an explicit locally installed executable/argv. No
network installation is attempted. The wrapper appends `--reporter=json` and
sets `PLAYWRIGHT_JSON_OUTPUT_FILE` to the new run's report path.

```sh
python scripts/shared/e2e_runner.py tests/e2e/coverage-manifest.json \
  --bindings tests/e2e/bindings.json --root . --runner playwright \
  --target local-test-build --output-dir test-results/e2e/run-002 \
  --timeout 300 -- node node_modules/@playwright/test/cli.js test tests/e2e
```

Use a new output directory each time: existing paths are never overwritten.
Output is restricted to `test-results/`, not source or workflow-state roots.
Relative manifest/bindings paths resolve against `--root`. Use sanitized target
labels and environment-provided credentials; never put secrets in argv or the
manifest. Native reports and logs may contain sensitive application data: run
only authorized tests on isolated data and protect the resulting artifacts.
The wrapper is not a security sandbox for untrusted test code.

pytest support is deliberately serial. `xdist`/distributed collection needs a
dedicated reporter and is not supported by this adapter. Playwright's native
workers and retries are supported within one runner invocation. This wrapper
does not merge distributed shards: a partial shard leaves unreported planned
cases `not_run`. Missing or duplicate projects/cases must not be hidden by
concatenating reports. Setup/dependency tests must also be explicitly modeled
and bound; untracked collected tests fail the evidence gate.

## Evidence and fail-closed completion

Each run preserves `manifest.json`, `plan.json`, `bindings.json`, `runner.log`,
`native-report.json`, `execution.json`, `results.json`, and `coverage.json`.
Execution errors preserve `error.json` and any available diagnostics instead of
a completion claim. The wrapper binds actual argv, runner exit code, timestamps,
source/test hashes, and original report hashes. Frozen inputs, sources, and test
bytes are verified again after execution; changed inputs invalidate the run.

pytest records collection and every setup/call/teardown event. A passing call
cannot erase failing teardown, expected failure, unexpected pass, or retries.
Playwright checks exact source/title/project bindings and preserves attempt
status, retry count, expected-failure disposition, and global errors. Its native
start timestamp must fall within the current invocation, with a small clock
allowance. Unknown statuses, duplicate IDs, missing reports, stale evidence,
and timeout/interruption fail closed. Timeouts terminate the launched process
group on POSIX; the Windows process-tree path still requires native validation.

Exit **0** means `complete_against_frozen_scope`; **1** means `incomplete`;
**2** means invalid input/evidence or execution failure. A filtered run and
`--collect-only` cannot close a full manifest. Failed, skipped, flaky, and
never-run cases do not count toward successful requirement/interaction coverage.
The original runner must also exit successfully.

A local runner can still lie, tests can assert the wrong behavior, and a manifest
can omit a feature. Hashes and normalized reports are provenance/consistency
checks, not remote attestation or proof of complete discovery. Keep independent
inventory/assertion review, explicit discovery gaps, external-boundary gaps,
visual acceptance, and the existing Review/Accept gates.

## Verification boundary

`tests/test_e2e_runner.py` has 48 tests at this revision. Linux/Python 3.13.5/
pytest 9.0.2 was used for the local run. The sample is a disposable CLI backed by
SQLite, exercised through real subprocess entrypoints for role denial and
idempotent repeated submission. It does not modify or verify a user product.
Playwright cases are explicitly labeled parser fixtures; no browser was run.
Full repository, installation, wheel, Go, Python 3.11/3.12, and native Windows/
macOS verification remain separate readiness gates.

The native Playwright contract follows its official
[JSON reporter documentation](https://playwright.dev/docs/test-reporters#json-reporter)
and [JSON reporter implementation](https://github.com/microsoft/playwright/blob/main/packages/playwright/src/reporters/json.ts).
The Python adapter consumes [pytest runtest reporting hooks](https://docs.pytest.org/en/stable/reference/reference.html#pytest.hookspec.pytest_runtest_logreport).
