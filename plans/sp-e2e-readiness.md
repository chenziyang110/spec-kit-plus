# SP E2E implementation readiness

## Product contract

E2E is scenario-first test analysis/design across desktop/mobile clients, web,
CLI and services. A visual model with actual inspection/interaction tools is a
first-class execution route; browser runners and executable test files are not
entry requirements. Models derive semantics; deterministic helpers account for
declared coverage and evidence. Test Design remains optional read-only input;
formal delivery still requires `tasks -> implement -> review -> accept`.

The scenario book covers operation assumptions, fourteen applicability
categories, source-bound requirements, concrete actions/oracles, and every
selected external-event/checkpoint pair. The rename guide contains 26 candidate
families. A missing interaction tool or unknown oracle is a gap, never a reason
to drop the case. Visual observations do not replace independent effect readback.

## Implemented source and integration

- Classic and independent Advanced workflows, the scenario helper and schemas,
  constrained t-way helper, optional pytest/Playwright adapters, and desktop
  Tk/filesystem sample are committed on the E2E feature branch.
- `21795c7` registers test-asset cognition closeout in the matching Go and JSON
  owners, preserving adjacent workflow ownership and adding alias/copy tests.
- `4b2c0e6` integrates Python/Go Learning, dispatch, reserved command names,
  Claude argument hints, the Advanced surface map and original expected SPX
  catalog. It updates profile counts, README/handbook and both prompt closeouts.
  The original `tests/test_spx_skill.py` gains one catalog entry; no existing
  assertion or test was removed. The complete diff is 13 files, +76/-5 lines.
- Init guidance uses the existing native display mapper for E2E. The shared
  `_install_shared_infra` copies the four helper files recursively and records
  them in the `speckit` manifest; the agent's `setup()` alone is only rendering.
- New regressions separate 38 native-rendering cases from six real init/upgrade
  cases, including modified skills/helpers and additive profile installation.
  Five additional registration/source checks protect catalog, packaging inputs,
  ownership and init guidance. These are executable tests, not passing results.

The helpers write ordinary test assets/results, not workflow state. Retained
test-asset mutations use canonical `sp-e2e`; disposable run data does not justify
a fabricated mutation receipt. An old runtime rejecting that identity remains
an explicit compatibility blocker. This branch is not a published runtime.

## Verification by revision and boundary

| Evidence | What actually ran | What it does not establish |
| --- | --- | --- |
| Initial `0dbc55d` | 57 helper and four source tests, recorded historically | Current full-repository or installed-profile validation |
| Native runner through `2a8ad1f` | 48 local tests including a disposable CLI/SQLite application | Actual Playwright browser execution or downstream acceptance |
| Scenario-first `f9ee966` | 65 helper/schema/CLI, five new source and four unchanged source tests | Real visual-model execution; observations were synthetic checker fixtures |
| Desktop `57b6f779` and integration continuation | 34 real Tk event-loop/filesystem tests, rerun with required display under Xvfb; zero skips | 34 visual-model executions or native Windows/macOS validation |
| Registry `21795c7` and integration continuation | Five top-level tests including original JSON/Go consistency tests, rerun in the isolated package | Full runtime module, Learning CLI or runtime release compatibility |
| New installation/registration suites | Both files parsed successfully and uploaded blobs matched local bytes | The 44 installation/rendering and five registration tests have not run in a complete repository environment |

Current local reruns used Linux, Python 3.13.5 / pytest 9.0.2 and Go 1.23.2.
The standalone registry check used `GO111MODULE=off`; it is deliberately not a
claim that the full module supports that toolchain. The desktop check used
`SPECIFY_E2E_REQUIRE_DESKTOP=1` and `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` under Xvfb.
No historical/isolated counts should be added and relabeled full-product E2E.

The environment could not clone the private source via container Git because
DNS resolution failed. Authorized connector reads/writes supplied bounded live
source. Original full trees and minimal diffs were preserved; temporary assembly
ancestry is not included in the delivered feature commits. Whole-repository
imports, dependency sync, rendering/init runs and wheel build remain unverified.

## Required before merge

1. In a complete source checkout, run `uv sync --extra test`, then execute the
   existing SPX, integration, hook, cognition-closeout-generation and packaging
   suites plus `tests/test_e2e_registration.py` and
   `tests/integrations/test_e2e_installation.py`. Fix actual failures without
   weakening the original catalog or user-modification preservation checks.
2. Build/install the wheel in an isolated project; exercise Classic, Advanced,
   helpers, manifests, native invocation, repair and both installation orders.
   Source force-includes and inspected copier code are not installation evidence.
3. Run the complete Go module on the toolchain declared by `go.mod`, the complete
   Python suite, Python 3.11/3.12, and supported Windows/macOS environments.
4. Preserve the real-client visual inspection/interaction and independent-state
   verification boundary. The committed widget-driven sample is not evidence
   of perception. Actual browser execution for the optional Playwright adapter
   remains distinct. Distributed pytest and cross-shard merging are unsupported.
5. Require successful CI for the final feature commit. The previously inspected
   desktop run `36563979338` failed before retrievable steps/logs; log retrieval
   returned 404. Its cause was not established. Recheck current jobs rather than
   assuming billing, dependency or assertion failures from that historical run.

Keep PR #125 draft until these gates close. Do not merge, publish, change source
visibility or claim downstream E2E success on the strength of isolated tests.

## Condition-level continuation after 98c6c0f

Scenario book v2 adds source/requirement-bound condition families before cases
are chosen. Explicit partitions, states, rules and sequences retain every
variant; discrete boundary declarations derive L-1/L/L+1 with verified units
and separate expected outcomes. Specific scenario step/oracle bindings prevent
a broad dimension tag from hiding a missing boundary point. Sibling variants
cannot share the same stimulus step or oracle. Timing obligations stay separate.

Both profiles now require v2 for derive/check/audit; v1 data and default schema
remain readable for explicit compatibility inspection. Never relabel old books
or transplant old passing evidence. Audit reports condition and timing coverage
separately, crediting only clean passed scenarios; all unexecuted/failed/skipped/
blocked/flaky cases remain visible. No executable test file is required for the
visual route. See [condition-level coverage](../docs/sp-e2e-conditions.md).

This continuation ran two completed, exit-zero subprocess test batches in an
isolated Linux/Python 3.13.5/pytest 9.0.2 workspace with plugin autoload disabled:

```text
python -m pytest tests/test_e2e_scenarios.py -q
65 passed, zero skipped
python -m pytest tests/test_e2e_conditions.py -q
66 passed, zero skipped
```

JUnit reports and explicit child exit codes were checked. The original 65-test
file stayed byte-identical to blob `48d1b5c44efbc2efa40cb79c9e4c8c8289c31db3`.
The 66 new tests exercise detailed gaps, invalid/missing inputs, requirement/
source/oracle links, variant isolation, stale evidence, every nonpass outcome,
v1/v2 schemas, fail-closed CLI gates, both workflow source contracts, and a copied
standalone helper in generated-style paths including spaces. That helper-copy
smoke test is not real init, manifest coexistence, repair or wheel installation.

All new observations are explicitly synthetic checker fixtures, not fresh
client/model/browser execution. No full-repository, Go, other-Python-version,
Windows/macOS or successful cloud CI result is claimed by these 131 focused
checks. The installation, release-compatibility and CI gates above still apply.
