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

## Initial verification through 2026-09-29

| Evidence | What actually ran | What it does not establish |
| --- | --- | --- |
| Initial `0dbc55d` | 57 helper and four source tests, recorded historically | Current full-repository or installed-profile validation |
| Native runner through `2a8ad1f` | 48 local tests including a disposable CLI/SQLite application | Actual Playwright browser execution or downstream acceptance |
| Scenario-first `f9ee966` | 65 helper/schema/CLI, five new source and four unchanged source tests | Real visual-model execution; observations were synthetic checker fixtures |
| Desktop `57b6f779` and integration continuation | 34 real Tk event-loop/filesystem tests, rerun with required display under Xvfb; zero skips | 34 visual-model executions or native Windows/macOS validation |
| Registry `21795c7` and integration continuation | Five top-level tests including original JSON/Go consistency tests, rerun in the isolated package | Full runtime module, Learning CLI or runtime release compatibility |
| New installation/registration suites | Both files parsed successfully and uploaded blobs matched local bytes | The 44 installation/rendering and five registration tests have not run in a complete repository environment |

Those local reruns used Linux, Python 3.13.5 / pytest 9.0.2 and Go 1.23.2.
The standalone registry check used `GO111MODULE=off`; it is deliberately not a
claim that the full module supports that toolchain. The desktop check used
`SPECIFY_E2E_REQUIRE_DESKTOP=1` and `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` under Xvfb.
No historical/isolated counts should be added and relabeled full-product E2E.

The environment could not clone the private source via container Git because
DNS resolution failed. Authorized connector reads/writes supplied bounded live
source. Original full trees and minimal diffs were preserved; temporary assembly
ancestry is not included in the delivered feature commits. Whole-repository
imports, dependency sync, rendering/init runs and wheel build remain unverified.

## Initial remaining validation, 2026-09-29

This checklist records the first authoring environment. The complete Windows
checkout and scoped results below supersede its source/installation gaps;
unexecuted matrix, release and acceptance boundaries remain explicit.

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

PR #125 remained draft at that point. The maintainer subsequently requested
source consolidation and merge explicitly. That maintenance instruction does
not authorize publication, a visibility change or downstream acceptance claims.

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
checks. The source consolidation results below update the installation boundary;
release compatibility and unexecuted cloud CI remain separate.

## Windows source consolidation, 2026-09-30

Verification used a complete source checkout, `uv sync --extra test`, Python
3.13 on Windows, and the toolchain declared by `tools/specify-runtime/go.mod`.
Actual installation exposed Windows metadata comparison, initial Advanced
launcher binding and missing-entrypoint repair defects. The fixes retain
descriptor/path identity checks, manifest ownership, user-modification
preservation and junction rejection rather than weakening those gates.

| Completed local evidence | Scope and result |
| --- | --- |
| E2E suite | All 14 top-level E2E test files: 414 passed, three existing Windows symlink-permission skips, zero failures |
| Native desktop child | Separate nonactivated Windows desktop; all 34 cases passed; negative control produced 33 passes and one expected failure |
| Installation | 44 native rendering, real init and additive-profile checks passed, including both profiles and sh/ps |
| Affected owners | 473 closeout, Learning, packaging, registry, hook, adapter, handbook and guidance checks passed |
| Existing SPX/rendering | Final full rerun: 67 existing SPX checks and 19 unified runtime-rendering checks passed, zero skips |
| Missing-file repair | 21 shared Classic/Advanced repair checks and 20 Claude/Grok/Vibe native-finalization checks passed, including real Windows junction rejection and preservation of edited/untracked files |
| Runtime and manifest | New and existing Windows metadata, copy and repair regressions passed; expected platform skips remain visible |
| Go | All packages exercised successfully across the module run and repaired-package reruns; the final main-package run and `go vet ./...` succeeded |
| Packaging guards | 74 archive/probe guard regressions passed; source/archive byte and RECORD checks succeeded |
| Actual installed wheel | Fresh wheel-only environment: all four Codex sh/ps × Classic/Advanced installation-order cases passed, including user edits, missing-file repair, runtime revision, Learning identity and helper entrypoints |
| Audit/lint | Locked production dependency audit found no known vulnerabilities; source, workflow-artifact and affected Markdown lint passed |

The completed wheel probe is bound to source revision
`fca0eec980956e394d49a1073f203e10f2b3a6b5` and wheel SHA-256
`461c46d8b8bf7ace7e0e2a32868339beff475f08a1bd1bf0dc05c68a1687645c`.
All 83 selected E2E source/archive assets were verified before installation;
the isolated probe returned `installed_e2e_wheel_verified`, exit zero, and kept
all 72 actual command records. Later closeout edits affect documentation and
the Claude inventory test oracle only, not the installed source tested here.
The deliberate helper edit retains the documented `PARTIAL` repair status with
exactly that preserved file and no remaining diagnostics.

Native tests used `--capture=sys` to avoid pytest descriptor capture interfering
with Tcl initialization; the real widget operations and all 34 case assertions
remain unchanged. Native event execution does not establish visual-model
perception or optional live Playwright browser execution. Counts above overlap
and must not be summed into a full-repository Python result.

GitHub check annotations independently confirm that jobs did not start because
account payments failed or the spending limit needs increasing. Cloud CI is
unverified, including the complete Python suite, Python 3.11/3.12 and Linux/macOS
matrix. This record qualifies source maintenance integration only; no runtime
release, anonymous consumer verification or downstream acceptance is claimed.
