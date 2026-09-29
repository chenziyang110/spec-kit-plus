---
name: spx-e2e
description: Advanced user-invoked scenario-first E2E testing for desktop, mobile, web, CLI, and services; systematically derive abnormal, boundary, state and timing cases, then execute through visual-model tools or suitable runners with explicit coverage gaps.
---

# Scenario-first E2E

Run only when explicitly invoked. Read `references/project-cognition.md` and
`references/project-learning.md`; use live evidence, not cognition, as truth.
Apply `references/execution-bootstrap.md` through the other-modifying-workflows
Work Board route. No new execution enum or runtime E2E API is implied. Use
supported help/discovery; do not impersonate a different workflow when a token
is unsupported. Read `references/blocker-resolution.md` at blocked boundaries.

The primary capability is test analysis and design, not a web automation wrapper.
Desktop/mobile clients are first-class: visual-model reasoning plus real UI
interaction may execute a scenario without test source or a browser runner.
Probe image inspection, capture, interaction, accessibility, fixture control,
independent state readback and runners separately. Do not infer capabilities
from the integration name. A visible screen without interaction is not execution;
an action without inspection is not proof of visual quality.

## Scope and ownership

Resolve the explicit project/feature and inspect the working tree. Full-product
E2E is not changed-files-only; narrower scope retains cross-feature regressions.
Do not infer a feature from a branch. Own scoped test assets, fixtures, adapters,
harness configuration and ordinary results only. Product behavior, migrations,
approvals, Test Design publications and feature lifecycle state remain outside
scope. Product defects keep reproductions and return to their owner; do not
weaken assertions or invoke another workflow implicitly.

Use isolated authorized accounts/data, readiness checks, deterministic fixtures,
per-worker namespaces, reset/cleanup, actual build/OS/device/entrypoint notes.
External mutations target disposable fixtures only. Production actions, real
payments/messages, credentials, dependency installation/upgrades, licensing and
external writes retain their authorization gates. Missing tools/dependencies are
blocked tests, not a mock-only substitution or a smaller scope.

## Discover, challenge assumptions, derive

Read `references/scenario-design.md` before authoring the book. Reconcile
intended requirements/acceptance/design with actual menus, APIs, commands,
objects, permissions, jobs, integrations and state. Test Design is optional,
read-only input through supported verification; preserve its IDs/gaps without
inventing a new projection consumer. Existing tests never define the universe.
Unknown/unread surfaces and contradictions remain discovery gaps.

For each stable operation identify its goal, object identity, real entrypoint,
assumptions, lifecycle and side effects. Challenge assumptions initially, during
execution, on retry and in risky combinations. Use error guessing, equivalence
partitioning, boundary value analysis, decision tables, state-transition and
event-sequence testing together. Unknown expected behavior is an oracle gap.
Pairwise factors do not discover missing conditions or establish event order.

```text
python .specify/scripts/shared/e2e_scenarios.py catalog
python .specify/scripts/shared/e2e_scenarios.py schema --schema-version 2
python .specify/scripts/shared/e2e_scenarios.py derive tests/e2e/scenarios.json --root . --require-v2
python .specify/scripts/shared/e2e_scenarios.py check tests/e2e/scenarios.json --root . --require-v2
```

Decide every catalog dimension for every operation, with concrete source-backed
not-applicable reasons; add product-specific dimensions. Do not label one happy
path with unrelated dimensions. Bind source_revision and hashes of selected
requirements/source/config/fixtures. Keep a scenario book with requirements,
operations, dimensions, observable checkpoints, events and concrete cards.
Each card has preconditions, ordered actor/action/observation steps, explicit
perturbation step bindings, oracles with assertion/channel/check, execution route,
priority, safety and cleanup. Preserve design/source-continuity IDs; read
`references/ui-quality-gate.md` when applicable. This book is a test asset,
not runtime workflow state, a Test Design publication, or human acceptance.

The helper derives every declared event x checkpoint obligation. Deletion before
opening a dialog is not deletion just before confirmation; external rename and
replacement at the original path are different events. Prove the mutation at
its precise checkpoint; use a deterministic barrier/test hook for narrow races.
A guessed sleep is not timing evidence. Keep unobservable timing cases blocked.
For rename inputs, resolve actual platform/product legality, name/path limits
and length units before choosing below/at/above values; never guess a universal
limit or expected error UI. Preserve identity/content and independent readback.

`scenario_design_ready` means declared design accounting only, not tests passed.
Prioritize risk without deleting the unexecuted denominator. Explicit
planning-only requests stop after the book; otherwise continue through feasible
execution and retain concrete capability blockers for the remainder.

## Condition-level denominator

New books use `schema_version: 2` and source/requirement-bound `conditions`.
Enumerate `variants: [{id, input, expected}]` for partition/state/rule/sequence/
example families. A boundary declares `{limit, unit, expectations: {below, at,
above}}` under `boundary`; derive L-1/L/L+1 in the verified discrete unit, never
guess a universal filename limit or an unknown oracle. Every applicable
dimension needs a family unless event x checkpoint accounting already owns it.

Every scenario includes `condition_bindings: [{condition, variant, step_ids,
oracle_ids}]`: ordered stimulus IDs and exact outcome assertions, with distinct
steps/oracles for sibling variants. Labels alone cannot close a dimension.
Use `--require-v2` on all book gates; v1 remains explicit legacy inspection,
not a downgrade escape. New conditions invalidate the book/trace binding and
need fresh execution. Report condition_coverage and timing_coverage separately;
failed/skipped/blocked/not_run/flaky scenarios never credit clean coverage.
Neither equality checks nor accounting prove semantic or perceptual truth.

## Execute with visual tools or an appropriate runner

Select visual, runner, hybrid or human execution per card. For clients prefer
available model inspection and UI tools; fixture tools may set up external
changes and independent oracles. No automation harness is required. Observe the
initial screen/target, perform bounded actions, capture/check actual outcomes,
and reacquire controls after state/layout changes rather than replaying stale
coordinates. Preserve action/checkpoint evidence and cleanup observations.
A screenshot is not proof of durable files/server state: use independent
filesystem/API/CLI/database/log readback for side effects. Missing oracles remain
blocked even when the screen appears correct.

Keep expected and actual observations separate. Preserve each attempt; failed
then passed is flaky. Failed/skipped/blocked/disabled/quarantined/not_run cases
are not passes. Test-harness repair stays bounded and agent-owned; retain failed
product evidence. New discoveries expand the book and invalidate its digest.
Changes to source, tests, configuration or fixtures need fresh evidence. Use a
new immutable run with actual target/build, capture times, step/oracle evidence,
and cleanup; do not convert visual observations into invented runner output.

```text
python .specify/scripts/shared/e2e_scenarios.py audit tests/e2e/scenarios.json --root . --trace test-results/e2e/run-001/trace.json --require-v2
```

The audit checks book_sha256, source_revision, current source/evidence hashes,
all declared step/oracle observations for passes, matching evidence channels,
cleanup and every scenario ID. It is local consistency, not attestation that a
model acted, inspected pixels or asserted the right thing. It requires no
pytest test_ref or Playwright project for visual cases.

## Optional combination/native automation lane

Use e2e_coverage.py only after discovering dimensions and ordered journeys.
Ordinary pairwise is not exhaustive; mandatory known-risk higher-order cases
survive selection. Critical bounded matrices can use higher strength or
exhaustive enumeration. Invalid user actions needing rejection are negative
tests, not infeasible constraints. Budget failure cannot silently lower strength
or sample; partition only while preserving cross-feature obligations.

```text
python .specify/scripts/shared/e2e_coverage.py plan tests/e2e/coverage-manifest.json --root . --max-cases 1000
python .specify/scripts/shared/e2e_coverage.py audit tests/e2e/coverage-manifest.json --root . --results test-results/e2e/run-001/results.json --max-cases 1000
```

Preserve the full generated case/variant set in scenario cards or tests and
reconcile IDs independently; the scenario checker does not calculate t-way
coverage. For serial pytest/local Playwright Test reuse e2e_runner.py with exact
bindings, full runner collection, actual attempts/exit codes, test_sources,
manifest_sha256, source_revision and native reports. The wrapper checks source/
test hashes before and after execution. Other harnesses need validated adapters;
never install one without authorization. Keep retries/global/teardown failures.
No distributed pytest or shard merging is supported; partial shards cannot
close a full manifest. Never hide runner failures in a shell pipeline. A visual
trace cannot override a failed native audit or certify t-way coverage.

## Audit and return

Independently review original operation/requirement discovery, applicability,
assumptions, boundary rules, event order, compound risks, assertions and original
evidence. When independence is unavailable, perform a documented second pass
and retain that qualification. No checker proves complete discovery or semantic
assertion adequacy. Report design coverage, execution coverage, observed
outcomes, combination coverage and visual acceptance separately, with all gaps,
exclusions, hashes and evidence refs. Missing visual comparison remains
pending-human-review. No absolute completeness, release safety or acceptance
claim. Formal delivery remains tasks -> implement -> review -> accept.

## Test-only asset mutation closeout

When retained test assets, harness configuration or behavior-bearing test docs
change, use `references/project-cognition.md` with canonical workflow `sp-e2e`
and the exact owned changed paths. Consume the supported planner/apply/recovery
contract; do not hand-write a receipt or invent an E2E stage/Activity. Disposable
run data and read-only planning do not justify a mutation receipt. Runtime
rejection is a compatibility blocker, not permission to impersonate a different
workflow. Use `references/project-learning.md` for relevant, evidence-backed
lessons; preserve explicit rule-promotion approval.

At a blocked exit retain stage, category, owner, exact cause, sanitized evidence,
attempted recovery, affected IDs, next action, observable unblock criteria and
exact resume point. Do not request secrets or transfer agent-capable repair to
the user. Resume by checking hashes/obligations, never stale chat memory. Close
Work only with its supported fresh verification, never a fabricated pass.
