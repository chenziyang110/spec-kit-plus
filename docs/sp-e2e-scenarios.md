# Scenario-first E2E: clients, visual models, and test analysis

The core of `sp-e2e` / `spx-e2e` is deciding **what must be tested**, not requiring
an executable browser suite. A desktop client can be tested by a capable visual
model using real screenshot/interaction tools, with auxiliary tools preparing
fixtures and independently checking effects. Browser, CLI/API and native-runner
routes remain available; none defines the universe of product behavior.

The professional umbrella is test analysis and design. This workflow combines
error guessing, equivalence partitioning, boundary value analysis, decision
rules, state transitions and event-sequence reasoning. Combination selection
comes after discovery. An algorithm cannot cover a condition that was never
modeled. The method draws on [ISTQB test analysis and design](https://istqb.org/certifications/certified-tester-foundation-level-ctfl-v4-0/)
and [NIST event-sequence testing](https://csrc.nist.gov/Projects/automated-combinatorial-testing-for-software/combinatorial-methods-in-testing/event-sequence-testing).
A resource changed between checking and using it may present a
[TOCTOU risk](https://cwe.mitre.org/data/definitions/367.html); a scenario alone
is not evidence of an actual vulnerability.

## Method and deliverables

First reconcile requirements and the real operation inventory, independently of
existing tests. For each operation list its user goal, entrypoint, object
identity, assumptions, lifecycle and effects. Challenge assumptions initially,
at each meaningful execution stage, after recovery and in related high-risk
combinations. Every standard dimension receives an applicability decision with
source evidence; unknown applicability or oracle behavior stays a discovery gap.
Lack of an automation tool is not an inapplicable product condition.

The source-bound **scenario book** is an ordinary test asset, not a Test Design
publication or a new runtime state machine. Its concrete cards describe setup,
ordered steps, external-change timing, assertions, observation channels, safety,
cleanup, execution route and risk priority. The model authors those semantic
choices. The helper checks declared accounting and source/evidence consistency;
it does not invent a product's correct behavior.

| Artifact/check | What it establishes | What it does not establish |
| --- | --- | --- |
| Operation/dimension ledger | Every declared operation's standard dimensions have decisions. | Discovery found every feature or decisions are justified. |
| Event/checkpoint matrix | Each declared event at each selected time has a scenario. | A race really occurred during execution. |
| Scenario book check | Requirements/dimensions/timing are mapped and cards have required fields. | The assertions are correct or tests executed. |
| Visual/mixed trace audit | All declared passes have source-bound step/oracle/cleanup observations and matching evidence channels. | Captures are authentic, a model actually saw them, or the product is accepted. |
| Native runner audit | The selected automation denominator, attempts, exit and evidence reconcile. | Visual acceptance or exhaustive discovery. |

## File rename: candidate scenario matrix

This is a derivation example, not a fixed filename policy or a report of tests
that were run. Select actual supported OS/filesystem/product rules and intended
outcomes first. `L` below is a verified product/platform limit, including its
measurement unit; it is not a universal constant. Unknown rules are oracle gaps.

| ID | Scenario condition | Timing/observation to preserve |
| --- | --- | --- |
| RN-01 | Normal rename of an existing file | Observe feedback and independently verify new path and unchanged contents. |
| RN-02 | Original absent before initiating rename | Test the actual stale-selection/entry behavior; do not simulate successful entry. |
| RN-03 | Original deleted after dialog opens | Prove absence before continuing to confirm. |
| RN-04 | Original deleted after editing, before confirm | Distinct from RN-03; preserve entered value and actual recovery behavior. |
| RN-05 | Original renamed externally while dialog is open | Check the intended identity/path contract, not a guessed name-following rule. |
| RN-06 | Original moved externally before confirmation | Verify no unrelated object is changed at the stale path. |
| RN-07 | Original deleted and another file created at its old path | Preserve distinct sentinel contents; prove the replacement is not unintentionally renamed. |
| RN-08 | Destination already exists | Verify declared overwrite/rejection semantics and preserve both objects' data. |
| RN-09 | Destination created by another actor just before commit | Use an observable barrier; a timer alone cannot prove the race. |
| RN-10 | Permission revoked after dialog opens | Distinguish feedback, actual effect and recovery after restoring permission. |
| RN-11 | Open/locked object changes availability | Apply the actual platform/product lock contract. |
| RN-12 | Empty and whitespace-only input | Separate product trimming/validation rules and actual persisted name. |
| RN-13 | Product/platform-invalid name class | Derive exact forbidden values from evidence, not a universal character list. |
| RN-14 | Name length L-1, L, L+1 | Expand to distinct cards and verify the actual byte/code-unit/character rule. |
| RN-15 | Full-path boundary independent of name length | Use a safe temporary hierarchy and independently inspect resulting paths. |
| RN-16 | Supported Unicode, normalization/case-equivalent names | Separate display equivalence from actual name/identity semantics. |
| RN-17 | Same name or case-only rename | Determine whether this is no-op, supported rename or rejected input. |
| RN-18 | Double confirm / Enter followed by click | Check at-most-once effects and no extra rename after the first completion. |
| RN-19 | Cancel, then reopen | Check original state and absence of unintended persisted edits. |
| RN-20 | Failure, edit the name, then retry | Keep the failure attempt; verify intended recovery without changing the oracle. |
| RN-21 | Interruption/restart during a pending operation | Prove the chosen interruption point and independently read persisted state. |
| RN-22 | External change after commit but before UI refresh | Check stale feedback, refresh and other views without misattributing the first operation. |
| RN-23 | IME composition, paste, keyboard and focus | Test actual input mechanics and whether premature confirmation is prevented as specified. |
| RN-24 | Search, recent items, open document and another window | Verify consumer updates and continued operations, not only the primary list label. |
| RN-25 | Invalid input plus stale original plus destination conflict | Choose explicit high-risk decision-rule combinations and expected precedence from the contract. |
| RN-26 | Undo where supported, or recovery after rollback failure | Verify identity/content, final UI state and safe continuation. |

Do not collapse RN-02/03/04 into one "missing file" test. Define external events
and observable checkpoints independently. Selecting `deleted` and `renamed` at
`dialog-open` and `before-confirm` gives four timing obligations. The helper
will report the missing pair even when the other three have cases. A replaced
object is another event. More complicated event sequences need explicit cards;
this helper does not infer all permutations or replace a concurrency harness.

Each candidate must become a concrete test, a source-justified inapplicability
decision, or a visible gap. Time limits can prioritize tests but cannot turn an
unexecuted test into an exclusion. This matrix is not a substitute for product-
specific discovery and independent review.

## Helper commands and exact schemas

From the source checkout, use Python 3.11+ with the standard-library-only helper:

```sh
python scripts/shared/e2e_scenarios.py catalog
python scripts/shared/e2e_scenarios.py schema
python scripts/shared/e2e_scenarios.py derive tests/e2e/scenarios.json --root .
python scripts/shared/e2e_scenarios.py check tests/e2e/scenarios.json --root .
python scripts/shared/e2e_scenarios.py audit tests/e2e/scenarios.json --root . --trace test-results/e2e/run-001/trace.json
```

Generated profiles reference `.specify/scripts/shared/e2e_scenarios.py`; actual
installed-profile verification is a separate [readiness gate](../plans/sp-e2e-readiness.md).
`schema` emits separate Draft 2020-12 `book` and `trace` schemas. This is field
shape documentation, not a replacement for `check`/`audit` cross-link and hash
checks. All commands emit JSON to stdout; none edits a source, drives a GUI,
executes an input command, or writes workflow state. The caller can preserve
output in a new run directory. Relative book/trace paths resolve under `--root`.

| Command | Successful claim | Non-success |
| --- | --- | --- |
| `catalog` / `schema` | Questions / field shapes only | Invalid CLI use exits 2. |
| `derive` | `obligations_only`, with all current gaps | Malformed/stale inputs exit 2. Gaps are not execution results. |
| `check` | `scenario_design_ready` | `design_incomplete` exits 1; invalid/stale input exits 2. |
| `audit` | `evidence_complete_against_declared_scenarios` | `incomplete` exits 1; invalid/stale evidence exits 2. |

A book contains `schema_version`, `scope`, `source_revision`, hashed `sources`,
`requirements`, `operations`, `scenarios`, `discovery_gaps` and `exclusions`.
Every standard dimension from `catalog` appears in every operation's
`dimensions`; custom dimensions are additive. Decisions contain `disposition`,
`reason` and bound `source_refs`. Side-effecting operations cannot omit a
persistence decision or use only visual/accessibility/human oracles.

### Example card: deletion before confirmation

This is one card fragment, not a complete ready book. Its IDs reference an
operation, requirement and event/checkpoint in the surrounding source-bound book.
The actual target error/recovery UX must be grounded in the product contract.

```json
{
  "id": "RN-04",
  "operation": "file-rename",
  "title": "Original deleted after editing but before confirmation",
  "dimensions": ["external_mutation", "event_order", "persistence_consistency", "visual_interaction"],
  "requirements": ["RENAME-IDENTITY-001"],
  "technique": ["error-guessing", "state-transition", "event-sequence"],
  "priority": "high",
  "preconditions": ["Create disposable A.txt with known sentinel content and record unrelated files"],
  "steps": [
    {"id": "open", "actor": "visual-model", "action": "Open Rename for A.txt", "observe": "The actual dialog targets A.txt"},
    {"id": "edit", "actor": "visual-model", "action": "Enter B.txt without confirming", "observe": "B.txt is entered and confirmation has not occurred"},
    {"id": "delete", "actor": "fixture", "action": "Delete only the disposable original", "observe": "Independent readback proves A.txt absent before confirmation"},
    {"id": "confirm", "actor": "visual-model", "action": "Activate confirmation once", "observe": "Capture actual feedback and recovery state"}
  ],
  "perturbations": [{"event": "deleted", "checkpoint": "before-confirm", "step_id": "delete"}],
  "oracles": [
    {"id": "feedback", "channel": "visual", "assertion": "No false success and contract-consistent recovery UI", "check": "Inspect fresh feedback and interactive state against the contract"},
    {"id": "identity", "channel": "filesystem", "assertion": "No unintended replacement or unrelated file is renamed", "check": "Independently enumerate paths and compare sentinel contents"}
  ],
  "execution": "visual",
  "cleanup": ["Remove only the isolated fixture directory and verify cleanup"],
  "safety": ["Never use production or user-owned files"]
}
```

The execution route describes the main interaction. `visual` can still use a
filesystem tool for setup/readback. Without that readback capability the card
remains designed but execution is blocked; do not remove the effect oracle.

## Visual or mixed execution records

A trace binds `book_sha256` from `check`, the same `source_revision`, actual run
ID, target/build label, executor kind/name and timezone-aware start/finish times.
Its `evidence` rows contain `id`, `kind`, `path`, `sha256` and `captured_at`.
Capture times must fall in that run. Paths are normalized project-relative POSIX
paths; escapes, absolute paths, backslashes and source/evidence hash drift fail.

`results` contains one record per reported scenario ID and all its `attempts`.
A nonpass attempt records status and a concrete reason. A passed attempt requires
all ordered-step observations (`id`, actual `observation`, `evidence_ids`), every
oracle observation (same fields plus `outcome: passed`), and successful cleanup
with observation/evidence. Evidence kinds must match oracle channels. Missing
cases are `not_run`; failed-then-passed attempts remain `flaky`. Partial traces,
discovery gaps, unobserved oracles and unsuccessful cleanup cannot close a run.

Never prefill results from expected behavior. Obtain actual observations from
the live tools, retain original captures/action logs, and distinguish what the
model saw from what an independent tool measured. Reacquire controls after UI
changes. For a narrow race use supported barriers or controlled hooks; a sleep
is not proof of the intended interleaving.

Evidence kinds, timestamps and hashes are metadata consistency, not attestation.
The helper does not decode screenshots, verify that a model inspected them,
verify honest execution, discover omitted files or judge semantic correctness.
Tests deliberately use labeled synthetic observations to check this boundary;
no desktop/mobile E2E success is claimed by the helper test suite.

## Coexistence with the existing automation lane

Keep `e2e_coverage.py` and [native runner adapters](sp-e2e-runner.md) for selected
automation cases. After scenario discovery, expand applicable constrained
combinations with stable IDs and reconcile every selected variant into cards or
runnable tests. The scenario checker does not compute t-way coverage. Native
runner collection/attempt/exit/coverage audits remain required; a visual trace
cannot override a failing runner or certify missing shards as complete.

The final report separates design, execution, observed outcomes, combination
coverage and visual/human acceptance. Formal delivery still follows
`tasks -> implement -> review -> accept`; standalone scenario work does not
mutate Test Design state or authorize a release.
