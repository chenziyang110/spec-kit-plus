# Desktop scenario validation sample

This fixture exercises a real Tk desktop window and real disposable files. It is
not a production file manager, a browser demonstration, a universal filename
policy, or a claim about the user's application. The sample exists to verify
that E2E planning distinguishes input conditions, external changes and operation
timing, and that visual feedback is checked independently from durable effects.

## Run the sample

Use the repository environment and a display with Tk support:

```sh
uv run python tests/e2e_samples/desktop_rename.py
```

By default the sample creates a new temporary sandbox and cleans it on normal
exit. `--workspace <new-directory>` selects a retained, create-only disposable
sandbox for evidence inspection. An existing directory is rejected; the sample
never opens a project or production directory as a file-management target.

The explicit sample contract is:

- An existing regular file can be renamed without changing its contents.
- Empty/whitespace, reserved names and the sample's listed characters are
  rejected. The length limit is **32 Unicode code points**, deliberately chosen
  for this fixture; it must not become a product or operating-system assumption.
- A source deleted, externally renamed, modified or replaced after selection
  must not be silently retargeted. An existing destination must not be overwritten.
- Failed confirmation leaves the dialog available for correction or cancellation.
  Refresh reflects the current directory. Queued duplicate confirmation after
  successful completion is a no-op.

The sample uses same-filesystem hard links and unlink for no-overwrite behavior.
It is a controlled pre-confirmation timing fixture, not proof of atomic rename
semantics under hostile syscall races, permission correctness on every OS,
network filesystem behavior, or crash durability.

## Repeatable integration checks

On Linux with Xvfb and the project test environment:

```sh
SPECIFY_E2E_REQUIRE_DESKTOP=1 xvfb-run -a uv run pytest tests/test_e2e_desktop_sample.py --capture=sys --junitxml=desktop-results.xml
```

`SPECIFY_E2E_REQUIRE_DESKTOP=1` makes absent Tk/display support fail rather than
silently skip the desktop tests. The dedicated desktop workflow also rejects
empty JUnit output, failures, errors and skips. Its run result is separate from
source-level parsing of the workflow YAML.

For native Windows pytest runs, retain `--capture=sys`. Default OS-descriptor
capture can interfere with Tcl file-channel reads, producing intermittent
`No error` failures while loading existing Tk files. Python-level capture keeps
those descriptors intact; subprocess runner output is still recorded separately.
The [ttkbootstrap test configuration](https://github.com/israel-dryer/ttkbootstrap/blob/master/pyproject.toml)
documents the same Windows/Tcl interaction. A required display remains required.

The test module includes empty/invalid input classes; `L-1`, `L` and `L+1`;
Unicode; same-name behavior; destination creation by another actor; deletion
before entry; deletion/rename/replacement/content change at **both** dialog-open
and pre-confirmation checkpoints; cancel/reopen/retry; duplicate confirmation;
non-symlink confinement; and create-only sandbox behavior. Postconditions read
files independently, not through the application's readback method.

These are real Tk event-loop/filesystem integration tests. They drive widget
events and inspect widget state; they are **not** evidence of model perception.
No project must adopt Tk or install this fixture to use `sp-e2e`.

## Visual-model execution is a separate lane

For a real visual pass, observe screenshots and use available mouse/keyboard
controls; do not substitute widget method calls and label them visual-model
execution. A useful bounded scenario is:

1. Observe `A.txt`, select it and open the rename dialog.
2. Enter `B.txt` and inspect that the actual text is correct before continuing.
3. Delete only the disposable `A.txt` through an auxiliary filesystem tool.
   Independently confirm it is absent **before** clicking Confirm.
4. Click Confirm and inspect the error feedback and remaining dialog state.
5. Independently verify that `B.txt` was not created and `taken.txt` is unchanged.
6. Cancel, refresh and inspect that the list agrees with independent readback.

Retain action order, captures and hashes, auxiliary-readback records, unexpected
observations, recovery attempts, exact sample/source identity and cleanup.
Do not assume a keyboard shortcut selected all text: verify the field. During
the local visual checkpoint, Ctrl+A moved the caret instead of selecting all;
the actual `B.txtA.txt` value was observed and corrected before perturbation.
The original capture remains part of that execution history.

The same visual checkpoint found a clipped status label that value-only
assertions had missed. The sample height was corrected and a control-visibility
regression was added. Automated tests and actual visual inspection remain
different evidence, even when both now pass.

## Verification scope

On 2026-09-29 the sample and test module were rerun in an isolated Linux
workspace with Python 3.13.5, pytest 9.0.2 and Xvfb: **34 passed, zero skipped**.
This is not the repository dependency environment, a whole-repository test run,
native Windows/macOS verification, or cloud CI. Historical visual observations
remain distinct from this widget-driven rerun. Source blobs were checked against
the exact locally executed files before committing.

Run the existing helper and workflow suites separately:

```sh
uv run pytest tests/test_e2e_coverage.py tests/test_e2e_runner.py tests/test_e2e_scenarios.py tests/test_e2e_workflow_contract.py tests/test_e2e_scenario_workflow_contract.py
```

Then run package/build checks and the Go suites documented in
[Local Development](local-development.md). See
[E2E readiness](../plans/sp-e2e-readiness.md) for the remaining integration gates.

## Real desktop execution through the native coverage lane

`tests/test_e2e_desktop_runner.py` connects the existing planner, native pytest
reporter, process runner and coverage audit to the real Tk sample. It does not
mock those owners or manufacture a passing native report. Each isolated project
contains exact copies of the existing helpers and sample, a frozen manifest,
complete pre-run bindings and an ordinary parameterized pytest child test.
Copying helpers here is test setup, not evidence of `specify init` installation.

The declared sample inventory has **34 client conditions**, all driven through
Tk widgets: five valid/Unicode/boundary names, fourteen invalid name classes,
eight external-event/checkpoint pairs, destination conflict, pre-entry absence,
error recovery/duplicate confirmation, same-name behavior, and three explicit
compound failures. The compound cases check the sample's validation precedence:
invalid length plus missing source plus occupied target; missing source plus
occupied target; replaced source plus occupied target. These are source-grounded
sample rules, not proposed rules for other products.

Each event/checkpoint has its own ordered journey; unordered factor coverage
cannot stand in for the event sequence. The child verifies that the exact input
reaches the widget, observes actual feedback, independently reads file bytes,
checks visible status bounds, and destroys the window/removes its disposable
store during teardown. Callback exceptions cannot hide behind a passing body.
Native collection, setup/call/teardown events, process exit, fingerprints and
original logs feed the existing coverage audit.

Four outer regressions exercise the same declared denominator:

| Invocation | Passed | Failed | Not run | Required wrapper outcome |
| --- | ---: | ---: | ---: | --- |
| Full client run | 34 | 0 | 0 | Exit 0, complete against this frozen sample scope |
| Select only deletion immediately before confirmation | 1 | 0 | 33 | Exit 1, incomplete despite child exit 0 |
| Collect only | 0 | 0 | 34 | Exit 1, incomplete despite child exit 0 |
| Deliberately delete the source in an expected-success case | 33 | 1 | 0 | Exit 1, preserve the original failed case |

The final row is an explicit negative control for failure propagation: the
sample correctly rejects the injected deletion, so the expected-success test
fails. It is not a discovered product defect, a changed acceptance criterion,
or a reason to weaken the assertion. Every client sandbox must still be cleaned.

```sh
SPECIFY_E2E_REQUIRE_DESKTOP=1 xvfb-run -a uv run pytest \
  tests/test_e2e_desktop_sample.py tests/test_e2e_desktop_runner.py \
  --capture=sys --junitxml=desktop-results.xml
```

The dedicated CI keeps the original no-empty/no-skip gate and original sample
suite, runs the new native chain, and retains native reports/logs without
uploading test source or disposable project trees. Changes to the planner,
runner, reporter and shared test environment now also trigger that workflow.

On 2026-09-29, a partial Linux/Python 3.13.5/pytest 9.0.2 workspace with Xvfb
executed the original 34 tests and these four new regressions together:
**38 outer tests passed, zero skipped**. The nested child runs are the table
above, not 38 additional model-perception executions. The helpers, original
sample and original test module were byte-checked against their Git blobs.
This adds real desktop-to-native-audit integration evidence. It does not verify
scenario-book-v2 trace execution, wheel installation, full source imports, Go,
Windows/macOS, Playwright Test, visual-model perception or downstream acceptance.
Those existing readiness gates remain separate; clients still do not need a
runner or this sample to use the primary scenario-first visual workflow.

## Real client execution with a scenario-book-v2 trace

`tests/e2e_samples/desktop_scenario_trace.py` now exercises the primary scenario
book and trace format directly, independently of the optional native-runner
manifest. It is an opt-in repository sample, not a new installed framework.
It authors a fixed **22-scenario regression subset** before execution: normal
and Unicode names, empty/whitespace/disallowed inputs, 31/32/33-code-point names,
occupied targets, same-name/cancel-reopen, eight external-change/checkpoint
pairs, and three compound failure rules. The existing 34-condition native suite
is unchanged; these denominators describe different deliberately selected sets.

The book binds input-source hashes, condition variants, actual ordered steps
and outcome assertions. The driver operates real Tk widgets and checks files
without using the application's readback method. At each external mutation it
checks the current input/checkpoint and records independent before/after file
state, including file device/inode identity. The replacement cases deliberately
use identical contents in a new object: matching bytes alone cannot satisfy the
original-selection contract. Successful renames and unrelated files also retain
their independently observed object identities. Feedback, refreshed list and
mapped control geometry are recorded as
`accessibility`, never as screenshots or model perception. No passing attempt
is finalized until the observations match and window/sandbox cleanup succeeds.

```sh
# --output must be NEW. No existing evidence or user project is overwritten.
SPECIFY_E2E_REQUIRE_DESKTOP=1 xvfb-run -a uv run python \
  tests/e2e_samples/desktop_scenario_trace.py --output /tmp/desktop-v2-run-001

# Re-audit the real trace with the unchanged helper used by both profiles.
uv run python scripts/shared/e2e_scenarios.py audit book.json --require-v2 \
  --root /tmp/desktop-v2-run-001 --trace trace.json
```

`--case deleted-before-confirm` executes one case but keeps all 22 in the book:
1 passed and 21 not-run returns exit 1. `--plan-only` needs no display, writes a
valid design with no action/evidence records, and also returns exit 1 because
execution remains incomplete. Exit 0 requires all declared scenarios to pass;
invalid arguments or an existing output directory return exit 2. Every attempt
retains its own observations, including failed attempts and cleanup failures.
A failed-then-passed negative-control run remains flaky, never cleanly passed.

Outputs are `book.json`, `design.json`, `trace.json`, `audit.json`, `inputs.json`,
source snapshots in `inputs/`, and per-attempt JSON observations with timestamps
and hashes. The source revision is explicitly a content-snapshot digest, not an
invented Git commit. The existing desktop CI retains the full successful trace
and observations plus its checkout revision; it does not upload Python source
snapshots. For offline re-audit of those CI artifacts, restore the three files
listed in `inputs.json` from that exact checkout to their snapshot paths and
verify the recorded hashes first. Never overwrite a mismatched file to hide drift.

This subset explicitly excludes OS permission changes, crash/syscall durability,
other environments, unselected input/recovery families and visual acceptance.
Those scoped exclusions are fixed before probing tools. They must not be copied
as not-applicable decisions into a full-product plan: there, applicable missing
cases remain gaps. Missing Tk/display leaves selected cases blocked, rather
than silently removing them. The 88 condition obligations include per-scenario
file/list/feedback checks; they are not 88 independent scenarios. The eight
timing obligations remain separate. No claim of exhaustive discovery, visual
quality, native-platform compatibility or product acceptance follows from this
bounded trace audit.

`tests/test_e2e_desktop_scenarios.py` verifies the real complete/filtered/failed/
retried executions and schema/CLI consumption, then separately tests stale
sources, changed evidence, reversed steps, wrong oracle channels, missing exact
boundary cases, unavailable capabilities and cleanup failure. At authoring,
these 19 checks plus the original unchanged 34 sample checks ran on local
Linux/Python 3.13.5/pytest 9.0.2 under Xvfb: **53 passed, zero skipped**. This is
not a full dependency-environment, installation/wheel, Go, Windows/macOS or
cloud-CI pass. The earlier four native-runner tests are retained in CI and were
not included in this particular local rerun. All remaining installation and
final-CI gates in the readiness document still apply.
