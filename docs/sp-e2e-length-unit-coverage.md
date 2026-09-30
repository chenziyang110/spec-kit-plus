# Length units must be tested together with the input repertoire

A Unicode smoke case and an ASCII boundary case cover different conditions;
they do not establish that Unicode works at that boundary. The desktop sample
contracts on **32 Unicode code points**, not UTF-8 bytes or UTF-16 code units.
This is a sample policy, never a universal filename or operating-system rule.

## Reproduced detection gap

`tests/test_e2e_desktop_length_units.py` reuses the existing
`tests/e2e_samples/desktop_scenario_trace.py` and its unchanged 22-case catalogue.
It varies only the boundary inputs in separate, freshly bound scenario books:
31/32/33 repetitions of `文`, and 31/32/33 repetitions of `🧪`. Both repertoires
are read back from the actual Tk entry before confirmation. Files and identities
are independently inspected, and every attempt checks cleanup.

Four new outer regression cases cover two correct-source runs and two deliberate
wrong-unit controls. In each control only a disposable copy of the sample's
length expression is changed; repository/application source is never mutated.

| Source and input matrix | Actual result |
| --- | --- |
| Unchanged sample; Han boundary inputs | 22 passed; all 88 declared conditions and 8 timing obligations satisfied |
| Unchanged sample; non-BMP boundary inputs | 22 passed; all 88 declared conditions and 8 timing obligations satisfied |
| UTF-8-byte-counting mutant; original catalogue | All 22 cases still passed |
| Same mutant; three Han boundary cases | Below/at failed, above passed, other 19 retained as not_run |
| UTF-16-code-unit-counting mutant; original catalogue | All 22 cases still passed |
| Same mutant; three non-BMP boundary cases | Below/at failed, above passed, other 19 retained as not_run |

The two deliberately wrong implementations survive the separate short-Unicode
and ASCII-boundary cases. Their rejection of valid near-limit Unicode inputs is
caught only when the conditions interact. This is a mutation-based test-strength
check, not a discovered defect in the unmodified sample and not a mutation score
for the whole product. A green accounting audit cannot discover an omitted
interaction or establish that the scenario inventory is adequate.

The original ASCII matrix is not deleted. Each Unicode matrix is a separate
book with the same scenario IDs but different input/expected-outcome bindings;
evidence cannot be transferred between them. The original full 22-case suite
and all its assertions remain unchanged. The copied sample, driver, checker,
this extension's source and explicit unit-control metadata are hashed before
execution. No passing trace or native report is manufactured.

## Run and inspect

```sh
SPECIFY_E2E_REQUIRE_DESKTOP=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  xvfb-run -a uv run pytest tests/test_e2e_desktop_sample.py \
  tests/test_e2e_desktop_scenarios.py tests/test_e2e_desktop_length_units.py \
  --junitxml=desktop-length-units.xml
```

The existing desktop workflow includes the new tests and preserves v2 books,
design reports, audit reports, source hash manifests and per-attempt observations,
including negative controls. It retains the existing native-runner tests and
fail/no-empty/no-skip gate. It does not upload copied source trees or publish
runtime assets. Required Tk/display absence fails rather than silently skipping.

Local verification used Linux, Python 3.13.5, pytest 9.0.2 and Xvfb. The three
modules above ran with `python -m pytest`, not the unavailable `uv`-synced
repository environment: **57 passed, zero skips**, comprising the unchanged 34 sample tests,
19 existing scenario-trace regressions and four new length-unit regressions.
Nested client cases in the table are not additional outer pytest tests. These
are real widget/filesystem observations, not model-perception or native
Windows/macOS evidence. The separate native-adapter suite was not rerun in this
command; it remains in the existing CI job.

## Visual execution remains a separate claim

A separately retained local visual checkpoint used screenshot inspection,
PyAutoGUI mouse/keyboard interaction and independent filesystem readback to
execute deletion immediately before rename confirmation. It correctly remained
incomplete: one passed visual scenario and seventeen not_run against its own
pre-frozen 18-case exploratory book. It was not rebound to the concurrent 22-case
catalogue or counted as 22 visual passes. The duplicate exploratory test module
was not added to the branch. Its captures, exact book and source-bound evidence
remain a separate local verification attachment, not proof of this matrix's
visual acceptance or a completed installed workflow.

The complete repository dependency environment, 44 installation/rendering and
five registration checks, actual wheel init/upgrade/repair, full Python/Go and
successful final-commit CI remain separate gates. See
[desktop sample](sp-e2e-desktop-sample.md),
[condition accounting](sp-e2e-conditions.md), and
[distribution verification](sp-e2e-distribution.md).
