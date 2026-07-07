# Superpowers 6 SDD Artifact Review Contract Design

Date: 2026-07-07

Status: Approved in brainstorming

## Summary

Adopt the useful Superpowers 6.0 subagent-driven development lessons in Spec
Kit Plus without replacing the existing `sp-*` workflow model.

The design strengthens `sp-plan -> sp-tasks -> sp-implement` with stable
worker and reviewer artifacts:

- planning-level global constraints and task interface maps
- task packet fields that can compile into task briefs
- implementation-time `task-brief` and `review-package` files
- one task reviewer that returns both requirement-fit and quality verdicts
- compact task progress ledger data for resume
- final whole-branch review before implementation closeout
- first-class UI and design fidelity evidence in the same artifact path

The guiding rule is:

> Workers and reviewers should read files, not leader memory.

## Research Inputs

External release notes shaped this design:

- Superpowers v6.0.0: rewrites subagent-driven development around a single
  per-task reviewer, file-based task and review handoffs, explicit model
  selection, a progress ledger, pre-flight plan reading, and a final broad
  review. Source: <https://github.com/obra/superpowers/releases/tag/v6.0.0>
- Superpowers v6.0.3: moves SDD scratch files into a self-ignored working-tree
  directory because writing under `.git/` can be denied and root scratch files
  can be accidentally committed. Source:
  <https://github.com/obra/superpowers/releases/tag/v6.0.3>

Spec Kit Plus should absorb the artifact and review-contract lessons while
preserving its own `.specify/`, `FEATURE_DIR`, `WorkerTaskPacket`, and
`WorkerTaskResult` architecture.

## Problem

Spec Kit Plus already has strong packetized implementation and embedded
review preparation. The current implementation surface still has four gaps:

1. Post-implementation review is still described as a two-reviewer sequence:
   `spec-reviewer.md` followed by `code-quality-reviewer.md`.
2. Worker and reviewer context can still be over-delivered through prompts or
   chat summaries instead of stable, inspectable files.
3. Resume state exists in `implement-tracker.md`, but task-level progress is
   not yet represented as a compact ledger optimized for context recovery.
4. UI and reference-implementation fidelity evidence can be required upstream,
   but task review does not yet have one standard artifact path for screenshots,
   visual comparison, accepted deviations, or human-review fallback.

These gaps make long implementation runs more expensive, easier to drift, and
harder to audit after context loss.

## Goals

- Replace the default two-reviewer task path with one reviewer that returns a
  spec verdict and a quality verdict.
- Standardize `task-brief` files for implementation workers.
- Standardize `review-package` files for task reviewers.
- Preserve and extend existing `WorkerTaskPacket` and `WorkerTaskResult`
  contracts rather than replacing them.
- Add plan and task fields that make worker briefs and reviewer packages
  deterministic to compile.
- Make UI fidelity and design-reference evidence visible in task briefs, review
  packages, task reviews, and final closeout.
- Let `sp-auto`, resume audit, and closeout distinguish checked tasks from
  reviewed and accepted tasks.
- Keep artifact storage inside Spec Kit Plus generated-project conventions.

## Non-Goals

- Do not replace Spec Kit Plus workflows with the Superpowers SDD executor.
- Do not move generated-project state to `.superpowers/sdd/`.
- Do not remove legacy `spec-reviewer.md` and `code-quality-reviewer.md` in this
  release.
- Do not require pixel-perfect visual diffing for every UI change.
- Do not let reviewers modify the working tree.
- Do not use review artifacts to change accepted product scope, upstream
  specification truth, or locked design intent.

## Current State

Current useful foundations:

- `sp-tasks` already prepares embedded implement review metadata and task packet
  readiness.
- `sp-implement` already requires validated `WorkerTaskPacket` dispatch,
  structured `WorkerTaskResult` handoffs, real-entrypoint evidence when
  required, `implement-tracker.md`, resume audit, and final closeout summary.
- The UI design workflow design already introduces `DESIGN.md`, `sp-design`,
  `ui-brief`, `ui-target.html`, and fidelity evidence concepts.
- `Reference-Implementation` profile handling already carries stronger evidence
  terms through planning, tasks, and implementation.

Current mismatch with the desired contract:

- `templates/commands/implement.md` still names both legacy reviewer prompts as
  the default post-implementation review path.
- `templates/passive-skills/subagent-driven-development/SKILL.md` still teaches
  agents to run spec compliance review before code quality review.
- `templates/worker-prompts/spec-reviewer.md` and
  `templates/worker-prompts/code-quality-reviewer.md` split the review read
  into two passes.
- No single canonical `task-reviewer.md` prompt exists.
- No canonical implementation review directory structure exists for task briefs,
  review packages, task reviews, and branch review.

## User-Facing Workflow

The public command chain remains unchanged:

```text
sp-specify -> sp-plan -> sp-tasks -> sp-implement
```

No new public `sp-review` command is introduced.

The visible improvement is that implementation reports can now cite durable
review artifacts:

- task brief paths
- review package paths
- task review result paths
- ledger state
- branch review path
- implementation summary path

When UI work is involved, the same report also cites screenshots, visual
comparison evidence, accepted deviations, or human verification fallback.

## Artifact Layout

For every feature, `sp-implement` may create:

```text
FEATURE_DIR/implementation-review/
  task-briefs/
    T001.md
  review-packages/
    T001.md
  task-reviews/
    T001.json
  ledger.json
  branch-review.md
```

This directory is task-layer implementation review state. It may be committed
when the project wants review auditability. It is not a global scratch directory
and does not replace:

- `FEATURE_DIR/tasks.md`
- `FEATURE_DIR/task-packets/*.json`
- `FEATURE_DIR/worker-results/*.json`
- `FEATURE_DIR/implement-tracker.md`
- `FEATURE_DIR/implementation-summary.md`
- `FEATURE_DIR/workflow-state.md`

Large ephemeral screenshots, browser traces, temporary diff files, and local
tool logs may live under existing project-specific temporary directories when
needed, but the review package must point to the evidence path that the leader
used.

## Planning Contract

`sp-plan` must prepare implementation and review structure earlier so
`sp-tasks` does not rediscover it task by task.

### Global Constraints

`plan.md` and `plan-contract.json` should carry a `Global Constraints` block
when constraints materially affect implementation or review.

Examples:

- language, runtime, package, and version floors
- dependency limits
- naming and copy rules
- public API or CLI compatibility requirements
- `DESIGN.md` requirements
- `ui-brief.md` or `ui-target.html` requirements
- accessibility constraints
- performance budgets
- platform support boundaries

These constraints are copied or referenced into each affected task packet.

### Task Interface Map

`sp-plan` should record task-level interface expectations when the plan shape
already implies them:

- what a future task consumes
- what a future task produces
- shared files or registries that serialize work
- dependency order
- external or internal contract names
- UI surfaces that must preserve reference behavior

The interface map is planning guidance, not a public micro-task list. `sp-tasks`
turns it into executable task packets.

### Review-Risk Notes

`sp-plan` should flag choices that a reviewer may later reject or be unable to
verify from a diff:

- a plan-mandated workaround that looks like a quality defect
- a user-approved fidelity deviation
- a required manual check
- a real-entrypoint validation path that cannot be automated yet
- a UI comparison that requires browser or human visual review

Review-risk notes prevent workers and reviewers from relying on hidden leader
memory.

## Task Contract

`sp-tasks` remains responsible for executable task generation and packet
readiness.

Each task packet should include or derive these fields when relevant:

```json
{
  "task_id": "T001",
  "global_constraints": [],
  "interfaces": {
    "consumes": [],
    "produces": []
  },
  "review_inputs": [],
  "review_risks": [],
  "ui_fidelity_requirements": {
    "applicable": false,
    "level": "none | approximate | high",
    "design_inputs": [],
    "required_evidence": []
  },
  "controller_checks_required": []
}
```

The existing `WorkerTaskPacket` remains the machine-readable implementation
contract. These fields extend the packet shape; they do not create a competing
packet type.

`tasks.md` should stay human-readable. It should reference task packet paths and
brief expectations rather than duplicating long artifact content.

## Task Brief

Before dispatching a worker, `sp-implement` writes:

```text
FEATURE_DIR/implementation-review/task-briefs/T001.md
```

The task brief is the worker-facing short contract. It must include:

- task id and task text
- authoritative inputs
- required references already selected by the leader
- allowed read scope
- allowed write scope
- forbidden paths and forbidden drift
- global constraints that apply to the task
- consumed and produced interfaces
- done criteria
- validation gates
- required evidence
- UI fidelity requirements when applicable
- result handoff expectations

The worker prompt should point to the task brief and packet. The leader should
not rely on pasted summaries as the only carrier of requirements.

## Review Package

After worker completion and before review, `sp-implement` writes:

```text
FEATURE_DIR/implementation-review/review-packages/T001.md
```

The review package is the reviewer-facing file. It must include:

- task id
- task brief path
- worker result path
- changed files
- diff command or diff artifact path
- validation evidence
- RED and GREEN evidence when TDD applies
- consumer evidence
- must-preserve and consequence evidence when applicable
- UI screenshots, visual comparison, accepted deviations, or human-review
  fallback evidence when applicable
- known concerns reported by the worker

The review package must not coach the reviewer to ignore findings or pre-rate
severity. It may identify accepted deviations only when the upstream plan or task
packet already records them.

## Task Reviewer

Add:

```text
templates/worker-prompts/task-reviewer.md
```

The task reviewer is read-only. It reviews the task brief, review package, diff,
actual files, and evidence. It returns both requirement-fit and implementation
quality judgments in one pass.

The reviewer must be skeptical of worker rationales and must not treat worker
summaries as proof.

### Review Result Schema

`sp-implement` writes or normalizes reviewer output to:

```text
FEATURE_DIR/implementation-review/task-reviews/T001.json
```

Minimum schema:

```json
{
  "task_id": "T001",
  "spec_verdict": "pass | fail | cannot_verify_from_diff",
  "quality_verdict": "pass | fail | concerns",
  "findings": [
    {
      "severity": "critical | high | medium | low",
      "category": "spec | quality | evidence | ui_fidelity | plan_mandated_defect",
      "file": "path/to/file",
      "line": 1,
      "summary": "Concrete issue summary",
      "required_fix": "Concrete fix or escalation"
    }
  ],
  "controller_checks": [
    {
      "check": "Run or inspect the real entrypoint",
      "reason": "Requirement cannot be verified from the diff",
      "evidence_required": "Screenshot or command output path"
    }
  ],
  "plan_mandated_defects": [],
  "ui_fidelity_result": "not_applicable | pass | fail | needs_visual_or_human_review",
  "final_assessment": "accepted | fixes_required | controller_check_required"
}
```

### Acceptance Rules

- `spec_verdict=fail` blocks acceptance until the issue is fixed or routed
  upstream.
- `quality_verdict=fail` blocks acceptance until fixed or explicitly escalated.
- `quality_verdict=concerns` may pass only when concerns are recorded as
  accepted residual risk or follow-up work.
- `spec_verdict=cannot_verify_from_diff` does not fail the task by itself, but
  every `controller_checks` item must be satisfied before acceptance.
- `ui_fidelity_result=needs_visual_or_human_review` requires agent visual
  comparison first when available; otherwise human review is an explicit
  controller check.
- `final_assessment=accepted` is valid only when blocking findings and required
  controller checks are resolved.

## Task Progress Ledger

`sp-implement` should maintain a compact ledger in:

```text
FEATURE_DIR/implementation-review/ledger.json
```

It should also summarize the current state in `implement-tracker.md` so humans
can resume without opening JSON first.

Minimum ledger entry:

```json
{
  "task_id": "T001",
  "status": "pending | brief_written | worker_done | review_package_written | review_pending | fixes_required | controller_check_required | accepted | blocked",
  "task_brief": "implementation-review/task-briefs/T001.md",
  "worker_result": "worker-results/T001.json",
  "review_package": "implementation-review/review-packages/T001.md",
  "task_review": "implementation-review/task-reviews/T001.json",
  "controller_checks_open": [],
  "controller_checks_closed": [],
  "last_evidence": []
}
```

Ledger state complements checked boxes in `tasks.md`. A checked task is a claim;
an accepted ledger entry is reviewed execution evidence.

## Final Branch Review

After all implementation tasks are accepted and before final closeout,
`sp-implement` runs one broad read-only branch review and writes:

```text
FEATURE_DIR/implementation-review/branch-review.md
```

The branch review inspects the complete changed surface, not only individual
task diffs. It checks:

- feature-level spec coverage
- integration drift between accepted tasks
- global constraints
- UI/design fidelity obligations
- unreviewed changed paths
- stale or contradictory task reviews
- validation evidence gaps
- remaining open gaps in `implement-tracker.md`

The final `implementation-summary.md` and user-facing closeout must mention the
branch review path and any unresolved human-needed checks.

## UI and Reference Fidelity Carry-Forward

UI work uses the same artifact path, with stronger evidence fields.

When a task touches UI, TUI, CLI output, design-system tokens, or a
reference-implementation surface, the task brief must identify:

- design source files such as `DESIGN.md`, `ui-brief.md`, `ui-target.html`, or
  imported reference notes
- fidelity level: `approximate` or `high`
- user-approved deviations
- required viewport or state coverage
- screenshot, browser, terminal-output, or manual-review evidence
- agent visual comparison availability
- human review fallback when agent visual verification is unavailable or failed

The task reviewer may pass UI fidelity only when the required evidence exists.
Generic tests passed output is insufficient when the active profile requires
visual, reference, or real-entrypoint evidence.

## Resume and Auto Routing

`sp-auto`, resume audit, and `sp-implement` startup must treat ledger state as
authoritative task-layer evidence when present.

Rules:

- If `tasks.md` marks a task complete but the ledger lacks an accepted task
  review, resume at review or controller-check state.
- If a worker result exists but no review package exists, generate the package
  before review.
- If a task review requires fixes, resume repair before selecting new work.
- If controller checks are open, complete them before accepting the task.
- If all task ledger entries are accepted but `branch-review.md` is missing,
  resume at final branch review.
- If branch review finds blocking issues, route to repair or upstream workflow
  according to the existing embedded-review safe repair boundary.

## Legacy Compatibility

Keep these files in the first implementation:

- `templates/worker-prompts/spec-reviewer.md`
- `templates/worker-prompts/code-quality-reviewer.md`

They become legacy compatibility prompts. The default generated guidance should
point to `task-reviewer.md`.

Compatibility text should say:

- legacy prompts are retained for older downstream workflows
- new `sp-implement` task reviews use `task-reviewer.md`
- do not run both legacy prompts and the new task reviewer for the same ordinary
  task review unless a special migration/debug scenario explicitly requires it

## Integration Surface

Implementation planning must sweep at least:

- `templates/commands/plan.md`
- `templates/commands/tasks.md`
- `templates/commands/implement.md`
- `templates/worker-prompts/implementer.md`
- `templates/worker-prompts/task-reviewer.md`
- `templates/worker-prompts/spec-reviewer.md`
- `templates/worker-prompts/code-quality-reviewer.md`
- `templates/passive-skills/subagent-driven-development/SKILL.md`
- `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`
- integration addenda in `src/specify_cli/integrations/**`
- execution schemas under `src/specify_cli/execution/**`
- implementation audit and summary helpers
- artifact validation, state validation, checkpoint, preflight, and commit hooks
- `tests/test_alignment_templates.py`
- integration install tests that assert worker prompt files are packaged

## Validation Plan

Tests should prove:

- `specify init` installs `task-reviewer.md`.
- Legacy reviewer prompts are still installed.
- `sp-implement` default guidance names `task-reviewer.md` rather than the legacy
  two-reviewer sequence.
- Passive subagent guidance teaches one task reviewer with two verdicts.
- Task packet guidance includes global constraints, interfaces, review inputs,
  review risks, UI fidelity requirements, and controller checks when relevant.
- Artifact validation accepts the new implementation-review directory structure.
- Resume audit treats checked tasks without accepted task reviews as incomplete.
- Final closeout requires or reports the branch review path when ledger evidence
  exists.
- UI task contracts require visual or human-review evidence when fidelity terms
  demand it.
- Integration renderers and generated skill/command surfaces remain aligned
  across supported agents.

Manual verification for the implementation plan should include:

```text
git diff --check
pytest tests/test_alignment_templates.py
pytest tests/integrations/test_cli.py
```

Targeted hook and execution-schema tests should be added or updated based on the
final implementation shape.

## Risks and Mitigations

### Artifact Volume

Small tasks may feel heavy if every task writes multiple files. Mitigation:
allow minimal task briefs and review packages for light tasks, but keep the same
contract and paths.

### Prompt Drift

Changing only `templates/commands/implement.md` would leave passive skills and
integration addenda teaching old behavior. Mitigation: require a cross-surface
sweep and alignment tests.

### UI Verification Variance

Some agents cannot inspect screenshots or browser output. Mitigation: require
agent verification first when available, then human review fallback with explicit
controller checks.

### Branch Review Cost

Whole-branch review adds a final cost. Mitigation: it replaces repeated broad
re-review and catches integration drift that task-local review cannot see.

### Schema Sprawl

New fields could duplicate `WorkerTaskPacket` and `WorkerTaskResult`.
Mitigation: treat task brief, review package, and ledger as compiled views or
references around the existing packet and result schemas.

## Open Decisions Resolved

- Storage uses `FEATURE_DIR/implementation-review/`, not `.superpowers/sdd/`.
- The default review path is one task reviewer with two verdicts.
- Legacy reviewer prompts stay for compatibility in this version.
- `sp-plan`, `sp-tasks`, and `sp-implement` are all in scope.
- UI fidelity evidence is first-class in task briefs, review packages, task
  reviews, and final branch review.
- Human review is a fallback when agent visual comparison is unavailable,
  inconclusive, or explicitly requested.
