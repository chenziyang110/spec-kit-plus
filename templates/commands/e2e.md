---
description: Systematically derive E2E tests for desktop, mobile, web, CLI, and service operations; cover abnormal inputs, boundaries, external changes and event order, then execute through available visual-model or runner tools without hiding gaps.
workflow_contract:
  when_to_use: Explicitly requested project-wide, feature-scoped, or regression E2E work; scenario design can precede execution and does not require a web project or an automation harness.
  primary_objective: Identify the complete declared operation inventory, challenge its assumptions, design concrete observable scenarios, execute feasible scenarios through the actual product, and account for every unverified obligation.
  primary_outputs: A source-bound scenario book in the existing test tree, immutable per-run visual/action/readback evidence and audit, plus executable assets and native runner reports only for selected automation lanes.
  default_handoff: Return scenario-design and execution coverage separately with precise gaps; formal delivery still requires /sp.review followed by /sp.accept.
---

{{spec-kit-include: ../command-partials/common/user-input.md}}

# Scenario-First End-to-End Testing

The primary capability is **test analysis and design**, not a web-runner wrapper.
Desktop/mobile clients, web products, command-line tools, and services are equal
subjects. Use the model's reasoning to discover what should be tested and, when
available, its visual understanding with real interaction tools to execute it.
A visual-model test does not need a Playwright selector or executable test file.
A plan is not a test execution, and a green smoke suite is not full coverage.

{{spec-kit-include: ../command-partials/common/execution-bootstrap.md}}

## Ownership, Scope, and Capabilities

1. Resolve the explicit project/feature and inspect the working tree. Unqualified
   full E2E means the current product, not just the latest diff. A narrower
   feature/regression scope retains affected cross-feature journeys. Never infer
   a feature from a branch name; preserve unrelated work.
2. Read relevant Learning and use project cognition as navigation, verifying
   claims against current requirements, code/configuration, and official product
   entrypoints. Test Design is optional read-only input through its supported
   verification routes; retain its IDs/gaps. Do not create a Test Design `e2e`
   projection, mutate its publications, or require a feature Plan to start.
3. Probe live image inspection, screenshot capture, UI interaction, accessibility,
   filesystem/API observation, fixture setup, and installed runners separately.
   Do not infer them from the agent name. Inspection without interaction cannot
   execute a scenario; interaction without inspection cannot prove visual quality.
   Missing browser automation must not block a usable desktop visual route.
4. Own only scoped test plans, fixtures, tests, adapters, and necessary harness
   configuration. Product source, migrations, design approvals, feature state,
   deployment and production data are outside scope. Never weaken assertions to
   get green. Product defects return to their owner with a reproduction; do not
   silently invoke another workflow. Runtime help/discovery is authoritative:
   never invent `specify e2e`, `specify-runtime e2e`, or an `execution announce`
   E2E enum. Use the bootstrap's **other modifying workflows** Work Board route;
   unsupported runtime/cognition tokens are capability gaps, not permission to
   impersonate another workflow or hand-write runtime state.
5. Use isolated test accounts/data, deterministic setup, per-worker namespaces,
   reset/cleanup, service readiness and actual build/OS/device/entrypoint notes.
   External deletion/rename/permission changes target only explicit disposable
   fixtures. Production transactions, real payments/messages, credentials,
   dependency installation/upgrades, licenses and external writes require their
   existing authorization. An unavailable external dependency is a blocked test,
   never a reason to substitute a mock and call it full-stack coverage.

## 1. Discover Operations Before Selecting Test Cases

Reconcile intended requirements/acceptance/design contracts with implemented
menus, routes, commands, permissions, objects, jobs, integrations and persisted
state. Existing tests do not define the denominator. Give operations and
requirements stable IDs and source refs; record unread/unknown surfaces and
contradictions as discovery gaps rather than silently shrinking scope.

For each operation describe its user goal, real entrypoint, object identity,
preconditions, assumed invariants, lifecycle, dependencies and observable effects.
Write assumptions explicitly: for example, the file still exists, still denotes
the same object, has the required permissions, and the destination is available.
Challenge each assumption: false initially, invalidated during the operation,
restored before retry, or invalidated together with a related assumption.

Use the installed Python 3.11+ interpreter to retrieve the shared question set:

```text
python .specify/scripts/shared/e2e_scenarios.py catalog
python .specify/scripts/shared/e2e_scenarios.py schema --schema-version 2
```

For **every operation**, decide applicability for `happy_path`,
`input_partitions`, `input_boundaries`, `object_lifecycle`, `external_mutation`,
`event_order`, `permissions`, `conflict_concurrency`, `repeat_cancel_retry`,
`interruption_recovery`, `persistence_consistency`, `environment_compatibility`,
`visual_interaction`, and `cross_feature`. Add product-specific dimensions when
needed. A not-applicable decision needs a concrete reason and bound source;
missing tools, fixtures, time, or oracle knowledge are gaps, not inapplicability.
Do not label one happy-path case with every dimension to satisfy a checker.

## 2. Derive Concrete Scenarios, Including Event Order

Apply error guessing to assumptions and failure history; equivalence partitioning
to valid/invalid input classes; boundary value analysis to exact discovered limits
and units; decision tables to interacting business rules; state-transition and
event-sequence analysis to lifecycle and ordering. Use these as complementary
ways to discover test conditions, not synonyms for pairwise parameter coverage.
Unknown expected behavior is an oracle gap, not an invented product rule.

For rename, ask about missing/moved/externally renamed/replaced objects, a new
object at the old path, target-name conflicts, permission/lock changes, invalid
names, exact length boundaries, duplicate confirmation, cancel/retry, interruption,
other windows/search/open documents, and persisted contents/identity. Determine
actual OS/filesystem/product rules first; never hard-code a universal illegal
character set, maximum length, or whether length counts bytes or characters.
Include keyboard/IME composition, focus and pending feedback when applicable.

Separate these scenarios: absent before entry; deleted after opening the dialog;
deleted after editing but before confirming; change during a pending operation;
and change after commit but before UI refresh. Define observable checkpoints and
external events independently. Each selected **event x checkpoint** is a separate
coverage obligation. Prove that the change actually occurred at that checkpoint
before continuing. Use deterministic barriers or supported test hooks for a
narrow race; a guessed sleep or fast click is not proof of race coverage. If the
checkpoint cannot be reached or observed, keep its case blocked. A check/use
race may be a TOCTOU risk; do not diagnose a vulnerability from timing alone.

Freeze `tests/e2e/scenarios.json` (or the project's established equivalent) with
source_revision and hashes of every selected source/contract/config/fixture.
The ordinary test-asset book contains sources, requirements, operations,
applicability decisions, checkpoints/events, scenarios, discovery_gaps and
exclusions with scope/reason/owner. It is not runtime-owned workflow state.
Each scenario contains stable ID, operation, requirements, dimensions, technique,
priority, preconditions, ordered actor/action/observation steps, exact perturbation
step bindings, visual and independent-effect oracles, execution route, safety,
and cleanup. Each oracle names an assertion and how to observe it. Keep clear
expected and actual observations in different records.

```text
python .specify/scripts/shared/e2e_scenarios.py derive tests/e2e/scenarios.json --root . --require-v2
python .specify/scripts/shared/e2e_scenarios.py check tests/e2e/scenarios.json --root . --require-v2
```

`derive` expands timing obligations and exposes gaps; it does not invent correct
scenarios. `check` verifies declared accounting. `scenario_design_ready` is only
planning readiness, never tests passed. Review the generated gaps, author missing
scenarios, and rerun. Preserve high-risk compound situations explicitly; budgets
may prioritize execution but must never remove the unexecuted denominator.

### Concrete condition coverage, not dimension labels

Author new books as `schema_version: 2`. Add `conditions` with stable ID,
operation, dimension, kind, title, bound source_refs and requirements. For
`partition`, `state`, `rule`, `sequence` or `example`, enumerate distinct
`variants: [{id, input, expected}]`. A `boundary` instead declares
`boundary: {limit, unit, expectations: {below, at, above}}`; the helper derives
L-1, L and L+1 as distinct obligations in that verified discrete unit. It does
not generate suitable strings or choose the expected business rule. Unknown
limits, units, variants or outcomes remain discovery gaps, not guessed values.

Every scenario has `condition_bindings: [{condition, variant, step_ids,
oracle_ids}]`. Bind the actual stimulus steps in order and specific oracle IDs;
at least one bound oracle assertion must exactly equal the variant's expected
outcome. Sibling variants need distinct steps and oracles; a generic happy-path
step cannot satisfy all boundary points. Every applicable dimension needs a
condition family, except timing already accounted by event x checkpoint pairs.
A scenario's dimension label without a condition or timing binding remains a gap.

Use `--require-v2` at every derive/check/audit gate. The helper retains v1 reads
for explicit legacy inspection only; never silently downgrade, relabel a v1 book,
or carry old trace observations into new conditions. Author missing conditions,
rebind the whole book and run fresh evidence. Report `condition_coverage` and
`timing_coverage` separately: only cleanly passed scenarios credit obligations;
failed/skipped/blocked/not_run/flaky variants remain visible. These checks bind
declared semantics, not proof of correct discovery, perception or t-way coverage.

## 3. Execute Through the Available Product Surface

Choose `visual`, `runner`, `hybrid`, or `human` per scenario, based on actual
capabilities and required observations. Default client interaction work to visual
model + UI tools when available; auxiliary tools may prepare fixtures and verify
side effects. Do not spend the task building a new automation framework when
real client interaction and evidence capture already suffice.

For a visual/hybrid scenario, observe the initial screen and selected object;
perform a bounded action; capture the resulting state; compare it with the
specific expected checkpoint; continue only from the actually observed state.
Reacquire controls after layout changes instead of replaying stale coordinates.
Record screenshots and action observations at relevant checkpoints, including
external-change proof, final feedback, focus/recovery and cleanup. Preserve
registered design/source-continuity IDs. A screenshot is visual evidence, not
proof of file identity, durable storage, server state, or correct background work:
verify those through independent filesystem/API/CLI/database/log readback.
Unavailable effect oracles remain blocked or pending, even if the UI looks right.

Retain every attempt; fail-then-pass is flaky. Failed, skipped, blocked, disabled,
quarantined and not_run scenarios are not passes. Bounded test-harness repair is
agent-owned; product bugs keep their failed evidence. New discoveries append
scenarios and invalidate the old book binding; never manufacture old observations
for new cases. Source/config/test changes require fresh evidence. Keep immutable
run IDs, actual target/build identity, capture times, hashes, action observations,
oracle observations and cleanup in a new run-specific trace.

```text
python .specify/scripts/shared/e2e_scenarios.py audit tests/e2e/scenarios.json --root . --trace test-results/e2e/run-001/trace.json --require-v2
```

Bind book_sha256 to the exact scenario book. This is a visual/mixed trace
consistency audit, not an assertion that the model
really acted or saw pixels. It requires every declared step/oracle of a passing
case, matching evidence channels, verified cleanup and current source binding.
No test_ref, pytest result or Playwright project is required for visual cases.
Do not fabricate native-runner reports from visual observations.

## 4. Optional Combination and Native Automation Lanes

After discovering the dimensions and ordered scenarios, use the existing
`e2e_coverage.py plan` for applicable constrained factor combinations. Ordinary
pairwise strength is not exhaustive; known high-risk higher-order combinations
remain mandatory. Use higher strength or exhaustive bounded matrices where
needed. Invalid actions the product must reject are required negative tests,
not infeasible exclusions. Exclude only proven impossible configurations.
Budget failure requires explicit partition/budget/scope decisions retaining
cross-feature journeys, never silent sampling or strength reduction.

```text
python .specify/scripts/shared/e2e_coverage.py plan tests/e2e/coverage-manifest.json --root . --max-cases 1000
```

Preserve every generated E2E-* ID/variant and requirement mapping when expanding
scenario cards or runnable tests. Independently reconcile the full generated
case set to the scenario book; the scenario checker does not calculate t-way
coverage. For runner execution compare actual collection with the complete plan,
reject missing/unknown/duplicate IDs, and use the supplied e2e_runner.py for
serial pytest or local Playwright Test. Do not rebuild a supported adapter or
install a runner without authorization. Keep native reports, actual argv and exit
status, timestamps, test_sources hashes, manifest_sha256 and source_revision.
The native wrapper checks before/after source/test bytes and retains all phases,
retries and global failures. It does not support distributed pytest or shard
merging; a partial shard cannot close a full manifest. Other harnesses require
validated adapters. Never let shell pipelines hide runner failure.

```text
python .specify/scripts/shared/e2e_runner.py tests/e2e/coverage-manifest.json --bindings tests/e2e/bindings.json --root . --runner pytest --target local-test-build --output-dir test-results/e2e/run-001 -- tests/e2e -q
python .specify/scripts/shared/e2e_coverage.py audit tests/e2e/coverage-manifest.json --root . --results test-results/e2e/run-001/results.json --max-cases 1000
```

A scenario trace cannot override a failed native audit or certify t-way coverage.
These optional adapters are implementation choices, not entry gates for clients.

## 5. Independent Review and Truthful Closeout

Independently reconcile the original operation/requirement inventory, assumptions,
applicability decisions, boundaries, negative cases, event order, compound risks,
assertions, original observations and constraints. If no independent reviewer
exists, perform a documented second pass and retain the unverified-independence
qualification. Machine checks cannot prove that a feature or oracle was not
omitted. Test design completeness, execution coverage, observed outcomes,
combination coverage and visual/interaction acceptance are separate claims.

An explicit planning-only request returns the book and design gaps without
pretending execution occurred. Otherwise continue through feasible execution;
missing interaction/observation tools leave named execution blockers, not a
reason to abandon test design. Final reports include all failed/skipped/blocked/
flaky/not_run IDs, discovery gaps, exclusions, evidence refs and fresh hashes.
Missing visual comparison remains pending-human-review. Never claim absolute
completeness, product acceptance or release safety. Formal delivery remains
`tasks -> implement -> review -> accept`; E2E is additional evidence, not a bypass.

## Test-only asset mutation closeout

When this invocation changes retained test assets, harness configuration or
behavior-bearing test documentation, apply the shared closeout below using only
those explicitly owned changed paths. Disposable run data and read-only
planning/inspection do not justify a fabricated mutation receipt. The canonical
identity is `sp-e2e`; an older runtime rejecting it remains a compatibility
blocker, never a reason to impersonate Implement or Review.

{{spec-kit-include: ../command-partials/common/inline-project-cognition-update.md}}

{{spec-kit-include: ../command-partials/common/learning-layer.md}}

At a blocked exit preserve stage, category, owner, exact cause, sanitized evidence,
attempted recovery, affected IDs, next action, observable unblock criteria and
exact resume point. Keep agent-capable repair agent-owned; never request secrets
or ask the user to reconstruct runtime state. Resume by checking source/book
hashes and obligations; do not reuse stale evidence or silently retarget scope.
Close Work only after its actual supported verification, never a fabricated pass.
