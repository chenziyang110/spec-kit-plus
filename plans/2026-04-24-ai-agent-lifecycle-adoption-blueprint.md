# AI Agent Lifecycle Adoption Blueprint

Date: 2026-04-24
Repo: `F:\github\spec-kit-plus`
Objective: absorb the highest-value mechanisms from `F:\github\pskoett-ai-skills\skills` into `spec-kit-plus` without introducing a second state system, duplicate workflow surface, or runtime model.

## Executive Summary

This plan adopts the useful parts of the external skill suite as native `spec-kit-plus` product capabilities:

1. A stronger learning loop
2. A lightweight execution intent contract
3. A shared verification gate
4. A multi-agent implement-audit-fix loop
5. A durable eval layer for promoted rules

The plan explicitly does **not** copy the external repository's `.learnings/`, `.context-surfing/`, `.evals/`, `Entire CLI`, or `gh-aw` assumptions. `spec-kit-plus` already has first-party primitives for learning state, project-map freshness, structured delegated handoffs, and runtime coordination.

## Current Native Primitives To Reuse

- Passive learning memory already exists:
  - `.specify/memory/project-rules.md`
  - `.specify/memory/project-learnings.md`
  - `.planning/learnings/candidates.md`
  - `.planning/learnings/review.md`
  - implementation: [src/specify_cli/learnings.py](/F:/github/spec-kit-plus/src/specify_cli/learnings.py:1)
- Learning CLI surface already exists:
  - `specify learning ensure`
  - `specify learning status`
  - `specify learning start`
  - `specify learning capture`
  - `specify learning promote`
  - implementation: [src/specify_cli/__init__.py](/F:/github/spec-kit-plus/src/specify_cli/__init__.py:914)
- Structured delegated execution already exists:
  - `WorkerTaskPacket`: [src/specify_cli/execution/packet_schema.py](/F:/github/spec-kit-plus/src/specify_cli/execution/packet_schema.py:1)
  - `WorkerTaskResult`: [src/specify_cli/execution/result_schema.py](/F:/github/spec-kit-plus/src/specify_cli/execution/result_schema.py:1)
  - packet compiler: [src/specify_cli/execution/packet_compiler.py](/F:/github/spec-kit-plus/src/specify_cli/execution/packet_compiler.py:1)
  - result validator: [src/specify_cli/execution/result_validator.py](/F:/github/spec-kit-plus/src/specify_cli/execution/result_validator.py:1)
- Runtime-managed delegation already exists:
  - `specify team ...`
  - `specify result path`
  - `specify result submit`
  - implementation: [src/specify_cli/__init__.py](/F:/github/spec-kit-plus/src/specify_cli/__init__.py:2481)
- Resume and handoff state already exists for debug and quick flows:
  - debug persistence: [src/specify_cli/debug/persistence.py](/F:/github/spec-kit-plus/src/specify_cli/debug/persistence.py:1)
  - quick/debug template guidance already models resumable state and join points
- Brownfield grounding already exists:
  - `PROJECT-HANDBOOK.md`
  - `.specify/project-map/*.md`
  - passive hard gate: [templates/passive-skills/spec-kit-project-map-gate/SKILL.md](/F:/github/spec-kit-plus/templates/passive-skills/spec-kit-project-map-gate/SKILL.md:1)

## Adoption Principles

1. Reuse native state before inventing new directories.
2. Keep `sp-*` as the visible workflow surface.
3. Prefer shared, integration-neutral capabilities over Codex-only features when possible.
4. Make learning outputs machine-readable before adding more automation.
5. Add CI variants only after the interactive loop is stable.

## Explicit Non-Goals

- No new `.learnings/` directory
- No new `.context-surfing/` directory
- No new top-level `skill-pipeline` user command
- No dependency on `Entire CLI`
- No dependency on `gh-aw`
- No CI-first implementation

## Dependency Graph

```text
PR1: Learning aggregation foundation
  ├─> PR2: Intent contract + verification gate
  └─> PR4: Durable eval layer

PR2: Intent contract + verification gate
  └─> PR3: Multi-agent implement-audit-fix loop
```

Parallelism summary:

- `PR1` must land first because it stabilizes learning taxonomy and recurrence semantics.
- After `PR1`, `PR2` and `PR4` can proceed independently.
- `PR3` should wait for `PR2` because the audit loop should consume the shared verification and intent primitives instead of inventing parallel ones.

## PR1 - Learning Aggregation Foundation

### Goal

Turn the existing passive learning layer into a proper inspectable system with recurrence-aware aggregation and promotion-ready reporting.

### Why This PR Comes First

The repo already captures candidate learnings, but the current surface stops at capture and promotion. It does not yet provide a stable aggregation report, ranking, or promotion queue. Without that, later eval and automation work has no reliable source of truth.

### Context Brief

- Existing learning storage is implemented in [src/specify_cli/learnings.py](/F:/github/spec-kit-plus/src/specify_cli/learnings.py:1).
- `start_learning_session()` already auto-promotes some candidates and computes relevant candidate sets.
- `LearningEntry` already tracks `recurrence_key`, `signal_strength`, and `occurrence_count`.
- The external suite's `learning-aggregator` value should be translated into this native learning layer, not into a new `.learnings/` hierarchy.

### Scope

Add a first-party aggregation/reporting layer on top of existing learnings.

### Deliverables

1. New aggregation API in `src/specify_cli/learnings.py` or a sibling module such as `src/specify_cli/learning_aggregate.py`
2. New CLI command:
   - `specify learning aggregate`
3. Machine-readable aggregation payload including:
   - grouped patterns by `recurrence_key`
   - recurrence count
   - first/last seen
   - applies-to coverage
   - promotion readiness
   - recommended target: `learning` or `rule`
4. Human-readable report output under a native path such as:
   - `.planning/learnings/reports/YYYY-MM-DD.md`
5. Updated `learning start` payload to surface top warnings more directly for in-session pre-flight use

### File Touchpoints

- Update: [src/specify_cli/learnings.py](/F:/github/spec-kit-plus/src/specify_cli/learnings.py:1)
- Update: [src/specify_cli/__init__.py](/F:/github/spec-kit-plus/src/specify_cli/__init__.py:914)
- Add tests:
  - `tests/test_learning_aggregate.py`
  - `tests/test_learning_cli.py` or extend existing learning command coverage if present
- Possibly update docs:
  - [README.md](/F:/github/spec-kit-plus/README.md:167)
  - [docs/quickstart.md](/F:/github/spec-kit-plus/docs/quickstart.md:141)

### Design Constraints

- Keep the current `LearningEntry` as the primitive.
- Do not add a second source of truth outside `.specify/memory/` and `.planning/learnings/`.
- Promotion remains human or command mediated. Aggregation is advisory by default.
- Preserve backward compatibility for current `specify learning start/capture/promote` commands.

### Proposed Acceptance Criteria

- `specify learning aggregate --format json` emits stable grouped pattern output.
- Aggregation identifies:
  - promotion-ready patterns
  - approaching-threshold patterns
  - stale/unresolved patterns
- Aggregation can be run in a cold session without mutating existing files unless an explicit report-write flag is used.
- Existing `learning` commands continue to pass.

### Verification

Smallest proving commands:

```powershell
python -m pytest tests/test_learning_aggregate.py
python -m pytest tests/test_alignment_templates.py
```

PR-level proving command:

```powershell
python -m pytest
```

### Exit Criteria

- Learning aggregation exists as a first-party feature.
- The repo has a stable machine-readable pattern report format.
- The next PR can consume promotion-ready patterns without inventing new taxonomy.

### Rollback Strategy

- If report shape causes churn, keep the aggregation engine but hide the CLI surface behind JSON-only output until the schema settles.

## PR2 - Intent Contract And Shared Verification Gate

### Goal

Add a lightweight intent contract for execution and a reusable verification runner that all execution flows can share.

### Why This PR Matters

This is the direct translation of the highest-value pieces of `intent-framed-agent` and `verify-gate`. It reduces scope drift and false completion without introducing a second workflow layer.

### Context Brief

- `WorkerTaskPacket` already contains `objective`, `hard_rules`, `forbidden_drift`, `validation_gates`, and `done_criteria`.
- `DelegationSurfaceDescriptor` already models `intent` as `implementation` or `evidence` in [src/specify_cli/orchestration/delegation.py](/F:/github/spec-kit-plus/src/specify_cli/orchestration/delegation.py:1).
- `sp-implement`, `sp-debug`, and `sp-quick` already talk about join points, blockers, and structured handoff.
- Verification logic exists in pockets, especially in the debug graph, but not yet as a shared first-party runner.

### Scope

Introduce a shared intent/verification abstraction without changing the visible `sp-*` workflow topology.

### Deliverables

1. Shared verification runner module, for example:
   - `src/specify_cli/verification.py`
2. Shared verification result schema, reused by:
   - delegated worker results
   - debug resolution evidence
   - quick-task completion checks
3. Execution intent artifact for leader-owned workflows:
   - implement tracker
   - debug session state
   - quick status state
4. Template updates so `sp-implement`, `sp-debug`, and `sp-quick` require:
   - an explicit current outcome
   - constraints / forbidden drift
   - success evidence

### File Touchpoints

- Update: [src/specify_cli/execution/packet_schema.py](/F:/github/spec-kit-plus/src/specify_cli/execution/packet_schema.py:1)
- Update: [src/specify_cli/execution/result_schema.py](/F:/github/spec-kit-plus/src/specify_cli/execution/result_schema.py:1)
- Update: [src/specify_cli/execution/result_validator.py](/F:/github/spec-kit-plus/src/specify_cli/execution/result_validator.py:1)
- Update: [src/specify_cli/debug/graph.py](/F:/github/spec-kit-plus/src/specify_cli/debug/graph.py:1)
- Update templates:
  - [templates/commands/implement.md](/F:/github/spec-kit-plus/templates/commands/implement.md:1)
  - [templates/commands/debug.md](/F:/github/spec-kit-plus/templates/commands/debug.md:1)
  - [templates/commands/quick.md](/F:/github/spec-kit-plus/templates/commands/quick.md:1)
- Add tests:
  - `tests/execution/test_verification_runner.py`
  - extend `tests/execution/test_packet_schema.py`
  - extend `tests/execution/test_result_validator.py`
  - extend `tests/test_alignment_templates.py`

### Design Constraints

- Do not add a new top-level user workflow named `intent` or `verify`.
- Keep the leader as the owner of resume state and verification truth.
- Reuse current `validation_gates` instead of inventing a second verification vocabulary.
- Reuse current blocked-result semantics: blockers, failed assumptions, suggested recovery actions.

### Proposed Acceptance Criteria

- Implement, quick, and debug flows can all consume the same verification runner.
- The current execution state in leader-owned artifacts names:
  - intended outcome
  - forbidden drift
  - active verification route
- Result validation can assert that verification evidence matches expected gates.
- Templates and worker prompts remain aligned.

### Verification

```powershell
python -m pytest tests/execution/test_packet_schema.py tests/execution/test_result_validator.py tests/execution/test_verification_runner.py
python -m pytest tests/test_alignment_templates.py tests/integrations/test_integration_codex.py
```

PR-level proving command:

```powershell
python -m pytest
```

### Exit Criteria

- There is one reusable verification primitive for the repo.
- Execution flows have an explicit intent contract without a new workflow surface.
- PR3 can build audit rounds on top of the shared verify gate instead of embedding ad hoc compile/test logic.

### Rollback Strategy

- If intent schema changes are too invasive, keep new intent fields leader-local in trackers first and defer packet schema expansion to a follow-up patch in the same PR.

## PR3 - Multi-Agent Implement-Audit-Fix Loop

### Goal

Translate the external `agent-teams-simplify-and-harden` pattern into native `spawn_agent` plus `specify team` orchestration semantics.

### Why This PR Matters

Today the repo has strong delegated execution primitives, but weaker first-party support for explicit audit rounds after implementation. This PR upgrades multi-agent execution from "parallel implementation" to "parallel implementation plus structured audit and fix rounds."

### Context Brief

- The repo already has:
  - native delegation descriptors in [src/specify_cli/orchestration/delegation.py](/F:/github/spec-kit-plus/src/specify_cli/orchestration/delegation.py:1)
  - runtime-managed result channels via `specify team submit-result`
  - join-point and blocked-state semantics in templates and runtime state
- The external team skill assumes `TeamCreate` and `TaskCreate`. Those concepts should be translated into current batch, join point, and request-id concepts, not copied literally.

### Scope

Add a bounded implement-audit-fix loop for high-risk or multi-lane batches.

### Deliverables

1. Audit lane classification for current batch types:
   - simplify review lane
   - harden review lane
   - spec/completeness review lane
2. Review-round metadata in runtime state, for example under:
   - `.specify/codex-team/state/reviews/`
   - or an extension of existing batch/session records
3. Leader flow for:
   - dispatch implementation lanes
   - wait for batch join point
   - dispatch read-only audit lanes
   - compile fix tasks from findings
   - repeat within a bounded round cap
4. Structured finding envelope for audit results so the leader can classify:
   - critical/high/medium/low
   - patch vs refactor
   - blocker vs advisory

### File Touchpoints

- Update orchestration/runtime:
  - `src/specify_cli/codex_team/auto_dispatch.py`
  - `src/specify_cli/codex_team/batch_ops.py`
  - `src/specify_cli/codex_team/runtime_bridge.py`
  - `src/specify_cli/orchestration/delegation.py`
- Possibly add:
  - `src/specify_cli/orchestration/review_loop.py`
  - `src/specify_cli/execution/review_schema.py`
- Update templates and prompts:
  - [templates/commands/implement.md](/F:/github/spec-kit-plus/templates/commands/implement.md:1)
  - [templates/worker-prompts/implementer.md](/F:/github/spec-kit-plus/templates/worker-prompts/implementer.md:1)
  - [templates/worker-prompts/debug-investigator.md](/F:/github/spec-kit-plus/templates/worker-prompts/debug-investigator.md:1) only if evidence-review lanes are generalized
- Add tests:
  - `tests/codex_team/test_review_loop.py`
  - extend `tests/codex_team/test_auto_dispatch.py`
  - extend `tests/codex_team/test_runtime_bridge.py`

### Design Constraints

- No new parallel state system outside existing runtime/session records.
- Review lanes must stay read-only at the contract level.
- The leader remains the only authority for:
  - join-point closure
  - runtime summary
  - resume state
  - final completion
- Refactor-class findings are advisory unless explicitly approved by policy.

### Proposed Acceptance Criteria

- A high-risk batch can be marked as requiring review before the join point closes.
- Audit lanes return structured findings instead of prose-only summaries.
- The leader can convert accepted findings into a follow-up implementation batch.
- Round cap and blocked-state semantics are explicit and testable.

### Verification

```powershell
python -m pytest tests/codex_team/test_auto_dispatch.py tests/codex_team/test_runtime_bridge.py tests/codex_team/test_review_loop.py
python -m pytest tests/test_alignment_templates.py tests/integrations/test_integration_codex.py
```

PR-level proving command:

```powershell
python -m pytest
```

### Exit Criteria

- `spawn_agent` and `specify team` can support a first-party implement-audit-fix loop.
- Review gating is explicit for high-risk batches.
- Audit results are machine-readable and resumable.

### Rollback Strategy

- If runtime integration proves too large, ship the review loop first as leader-local orchestration guidance with machine-readable audit envelopes, then fold it into `specify team` records in a narrow follow-up patch within the same PR.

## PR4 - Durable Eval Layer For Promoted Rules

### Goal

Create a durable native eval surface that turns promoted learning and rule patterns into regression checks.

### Why This PR Matters

This is where the outer loop stops being advisory and starts preventing repeated failure. It is the correct long-term home for the useful part of `eval-creator`.

### Context Brief

- After PR1, the repo should have stable aggregated promotion candidates.
- Current testing and validation knowledge already exists in handbook/project-map outputs and packet validation gates.
- The eval layer should reuse the repo's own truth sources and CLI, not import the external `.evals/` format wholesale.

### Scope

Introduce a minimal native eval system aimed at promoted project rules and high-value repeated failures.

### Deliverables

1. New eval storage, for example:
   - `.specify/evals/index.json`
   - `.specify/evals/cases/*.md`
2. New CLI surface:
   - `specify eval create`
   - `specify eval run`
   - `specify eval status`
3. Minimal verification methods:
   - file existence / section check
   - rule text / phrase presence
   - command exit code check
   - optional path/pattern grep check
4. Promotion bridge:
   - promoted learning can optionally emit an eval candidate scaffold

### File Touchpoints

- Add:
  - `src/specify_cli/evals.py`
  - `src/specify_cli/eval_runner.py`
- Update:
  - [src/specify_cli/__init__.py](/F:/github/spec-kit-plus/src/specify_cli/__init__.py:1)
  - [src/specify_cli/learnings.py](/F:/github/spec-kit-plus/src/specify_cli/learnings.py:1)
- Add tests:
  - `tests/test_eval_cli.py`
  - `tests/test_eval_runner.py`
- Update docs:
  - [README.md](/F:/github/spec-kit-plus/README.md:167)

### Design Constraints

- Keep eval cases small and deterministic.
- Target promoted rules and durable invariants first.
- Do not build CI automation in this PR.
- Do not require external services or model-in-the-loop validation for the first release.

### Proposed Acceptance Criteria

- A promoted rule can generate an eval scaffold with a stable pattern key.
- `specify eval run` produces pass/fail/skip output against stored cases.
- Eval results are machine-readable and safe to use later in CI.
- Learning and eval terminology stay aligned.

### Verification

```powershell
python -m pytest tests/test_eval_cli.py tests/test_eval_runner.py
python -m pytest tests/test_learning_aggregate.py
```

PR-level proving command:

```powershell
python -m pytest
```

### Exit Criteria

- The repo has a first-party durable eval layer.
- Promoted rules can become executable regression checks.
- Future CI work can wrap this layer instead of inventing a second one.

### Rollback Strategy

- If the CLI surface feels premature, keep case storage plus runner internals and gate public commands behind a minimal `status` command until real cases accumulate.

## Cross-PR Review Checklist

Use this checklist at the end of every PR:

- Did this PR reuse native `spec-kit-plus` state instead of creating a parallel directory?
- Did this PR keep `sp-*` as the visible workflow surface?
- Did this PR preserve cross-CLI applicability when possible?
- Did this PR add machine-readable state before adding more automation?
- Did tests cover the new schema or runtime transitions, not just happy-path docs?

## Anti-Patterns To Reject

- Copying external `.learnings/`, `.context-surfing/`, or `.evals/` paths as-is
- Adding a new user-facing `skill-pipeline` command that competes with `sp-*`
- Making CI the first execution target
- Building Codex-only product features when the underlying primitive is integration-neutral
- Allowing workers to become the authority for resume or completion state

## Suggested Execution Order

1. Ship `PR1` fully
2. Start `PR2`
3. Once `PR1` lands, a parallel lane may start `PR4`
4. Start `PR3` only after `PR2` settles its intent and verification primitives

## Final Recommendation

If scope pressure forces a reduction, preserve the order below:

1. `PR1`
2. `PR2`
3. `PR3`
4. `PR4`

That sequence maximizes product value earliest:

- `PR1` gives the repo memory that can be inspected
- `PR2` makes execution safer
- `PR3` makes multi-agent execution higher integrity
- `PR4` makes learning durable over time
