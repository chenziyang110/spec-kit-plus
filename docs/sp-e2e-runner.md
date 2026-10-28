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

## Empty selection is still an accounted run

For serial pytest, a fresh native report with `collected: []`, no events or
collection/internal errors, and matching process/report exit code 5 (no tests
collected) is **incomplete**, not malformed evidence. An explicit harness that
normalizes that exit to 0 still receives no coverage credit. Every frozen case
appears as `not_run` in `coverage.json`, together with missing requirements and
interactions; `results.json` retains an empty actual-case list. The wrapper exits
1 and preserves the original runner exit code, report, log and hashes.

This covers a `-k` expression that matches nothing, deselecting every case,
filtered collect-only execution, and a module-level skip that collects no tests.
A skipped module does not prove that any individual frozen case executed: its
reason remains in the original runner log while those cases remain `not_run`.
Correct the selection or capability gap and run again into a new output directory;
do not remove the missing cases from the manifest to get a passing report.

Missing or malformed collection fields, foreign run IDs, exit mismatches,
collection/internal errors, events for uncollected cases, and other error exits
remain invalid. Missing reports and timeouts still fail closed. The Playwright
adapter's empty-report validation is unchanged; no equivalent native collection
proof is inferred from an empty Playwright report.

## Verification boundary

`tests/test_e2e_runner.py` contains the original 48 tests plus 19 empty-selection
and error-preservation regressions. Linux/Python 3.13.5/pytest 9.0.2 was used for
the local run. The sample is a disposable CLI backed by
SQLite, exercised through real subprocess entrypoints for role denial and
idempotent repeated submission. It does not modify or verify a user product.
Playwright cases are explicitly labeled parser fixtures; no browser was run.
Full repository, installation, wheel, Go, Python 3.11/3.12, and native Windows/
macOS verification remain separate readiness gates.

The 67 runner checks were also executed in one invocation with the unchanged
34 desktop-sample and four desktop/native-runner checks under required Xvfb:
**105 passed, zero skipped**. Six new real-process/CLI reproductions first failed
against the previous runner with `pytest collection: empty array`; after repair
they preserve all four planned cases as not-run and keep pytest's exit code 5.
This is focused runner/client validation in a partial source workspace, not a
full dependency installation, scenario-v2/model-perception pass or cloud CI.

The native Playwright contract follows its official
[JSON reporter documentation](https://playwright.dev/docs/test-reporters#json-reporter)
and [JSON reporter implementation](https://github.com/microsoft/playwright/blob/main/packages/playwright/src/reporters/json.ts).
The Python adapter consumes [pytest runtest reporting hooks](https://docs.pytest.org/en/stable/reference/reference.html#pytest.hookspec.pytest_runtest_logreport).

## Shared-evidence I/O and final freshness checks

Native results bind the same log, report and execution receipt to many cases.
The audit validates every run-level evidence declaration and every evidence
declaration for a **passed** case. It hashes each distinct path in that validated
set on first use and once again before returning. It streams file hashing instead
of loading an entire log into memory. The memo exists only inside that audit
call; the public `verify_files` helper and every subsequent run read fresh bytes.
Repeated declarations in that validated set still have their schema, normalized
digest and safe path checked: conflicting hashes, duplicate entries within a
passed case, empty required evidence and unsafe paths cannot acquire coverage
credit from a previously seen file.

Per-case evidence on `failed`, `skipped`, `blocked`, `not_run` and `flaky` records
is not read or validated by this audit. Treat it as unverified diagnostic metadata,
not accepted evidence. Such cases remain coverage gaps regardless of their
attached fields. Run-level evidence must still validate, even when no case passes.
A downstream consumer must perform its own required validation before relying
on non-passed-case diagnostic evidence; an incomplete coverage report does not
certify those declarations. This preserves the existing schema-v1 audit boundary.

The native wrapper separately freezes the original manifest and bindings before
parsing them, checks those original paths/bytes before launching the process,
after it exits, and again before publishing the final audit. Checking only the
normalized JSON copies is insufficient: whitespace-only original-file edits and
same-byte symlink retargets still invalidate the run. Absolute input paths remain
supported. A rejected post-run check retains native evidence and `error.json`
but never publishes a passing `coverage.json`.

Final reconciliation also rechecks the source and test bytes. Changes, deletion,
replacement and escaping symlink retargets observed during the closing reads
invalidate the audit, including an otherwise incomplete run. This adds detection
for late drift after initial validation. It is not an atomic multi-file snapshot,
a filesystem lock, or proof against a writer that changes and restores bytes
between observations. Keep the frozen sources and evidence immutable and
coordinate writers through the existing owner/resource gates.

The JSON schemas, case IDs, requirement denominator, retry dispositions and
exit meanings are unchanged. All failed, skipped, flaky and unexecuted rows
remain visible. There is no cross-run cache, distributed-shard merge, sampled
hash, mtime-only shortcut, or relaxation of independent acceptance. The indexed
planner remains deterministic and audits build the combination model only once.

Run the helper regression suite and then the real native/client consumers:

```sh
uv run pytest tests/test_e2e_coverage.py tests/test_e2e_coverage_planner.py \
  tests/test_e2e_evidence_io.py -q
uv run pytest tests/test_e2e_runner.py -q
SPECIFY_E2E_REQUIRE_DESKTOP=1 xvfb-run -a uv run pytest \
  tests/test_e2e_desktop_sample.py tests/test_e2e_desktop_runner.py -q
```

`test_e2e_evidence_io.py` checks fixed I/O work for 1, 8, 64 and 1,000 cases,
late source/test/evidence drift, per-case declaration validation, safe paths,
fresh subsequent calls and the complete status denominator. These are fixture
regressions, not a replacement for full-repository or installed-wheel tests.
The desktop/native suite separately proves that filtering, collection-only and
a deliberately injected failure cannot turn a 34-condition book green.

For performance comparisons, retain a trusted pre-change helper and run:

```sh
python tools/workflow-quality/benchmark_e2e_coverage.py \
  --baseline /path/to/trusted/e2e_coverage.py --repeats 5
```

The benchmark compares complete outputs on every iteration, alternates execution
order, and reports raw timings and source hashes. Alongside the original six
planner workloads, `shared-evidence` binds one 4 MiB JSON fixture to 128 cases.
Small runs may be slower because closing integrity checks add work; there is no
universal speedup or CI wall-clock threshold. Helper timings are not browser,
desktop, discovery, independent-review or full-workflow execution timings.
