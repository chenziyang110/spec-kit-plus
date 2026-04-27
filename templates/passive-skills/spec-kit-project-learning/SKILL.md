---
name: spec-kit-project-learning
description: Use this skill whenever you discover a recurring bug, workflow gap, missing project constraint, or global user preference in a Spec Kit Plus repository, OR when the user explicitly asks to "remember this", "add a rule", "update project memory", or capture a learning. It guides you on how to properly extract, record, and promote operational knowledge into the shared project memory layer using the `specify learning` CLI instead of trapping it in single-task chat memory.
origin: spec-kit-plus
---

# Spec Kit Project Learning

Spec Kit Plus uses a 4-layer shared memory system to prevent recurring mistakes and retain project-level operational knowledge across workflows (`sp-specify`, `sp-plan`, `sp-implement`, `sp-debug`, etc.). 

## The 4-Layer Memory Architecture

1. **Principle Layer (`.specify/memory/constitution.md`)**
   - Holds principle-level MUST and SHOULD governance.
   - Changes slowly and intentionally. Highest authority.

2. **Stable Rules (`.specify/memory/project-rules.md`)**
   - Preserves stable, shared project rules that affect multiple workflows.
   - Stronger than general learnings, weaker than constitution principles.

3. **Confirmed Learnings (`.specify/memory/project-learnings.md`)**
   - Preserves confirmed project learnings that are reusable but not yet principle level.
   - The main project-level improvement layer.

4. **Runtime Candidates (`.planning/learnings/candidates.md` & `review.md`)**
   - Stores noisy or newly observed candidate learnings.
   - Avoids polluting stable memory with one-off observations.

## When to Capture a Learning

As an Agent executing a workflow, you should actively identify and capture operational knowledge when you observe:

- **`pitfall`**: Repeated implementation traps or testing failures.
- **`recovery_path`**: Recovery sequences that repeatedly save time.
- **`user_preference`**: User corrections or style preferences repeated across features.
- **`project_constraint`**: Constraints repeated across features.
- **`workflow_gap`**: Planning-critical details repeatedly missed during `sp-specify` or `sp-plan`.
- **`routing_mistake`**: The run started in the wrong `sp-*` workflow or had to upgrade/downgrade route after friction.
- **`verification_gap`**: The run lacked the minimum credible validation path or discovered a broken testing assumption.
- **`state_surface_gap`**: Durable state failed to capture the information needed to resume, review, or auto-capture learning.
- **`map_coverage_gap`**: The handbook/project-map atlas lacked the dependency, lifecycle, ownership, or change-impact facts needed for safe work.
- **`tooling_trap`**: Toolchain, dev-server, watcher, environment, or observer behavior masqueraded as an application bug.
- **`false_lead_pattern`**: The symptom strongly resembled one cause, but reusable evidence showed the root cause family was elsewhere.
- **`near_miss`**: A risky path was avoided late enough that future workflows should learn from it.
- **`decision_debt`**: A vague or deferred decision repeatedly caused downstream workflow cost.

## Complementary Passive Skills

- `spec-kit-workflow-routing` decides which active `sp-*` workflow should run.
- `spec-kit-project-map-gate` decides whether brownfield work has enough handbook and
  project-map coverage to continue or must route through `sp-map-codebase` first.
- This passive skill starts and captures the shared learning stream once the correct
  workflow and brownfield context gate are in place.

## Command Roles

Each `specify` workflow has a specific role in consuming and producing learnings:

- **`sp-specify`**: Primary producer of `workflow_gap`, `user_preference`, and `project_constraint`.
- **`sp-plan`**: Primary producer of `workflow_gap` and `project_constraint`.
- **`sp-checklist`**: Focused producer of requirement-quality `workflow_gap` and checklist-shaping `project_constraint`.
- **`sp-tasks`**: Primary producer of reusable decomposition `workflow_gap` and execution-shaping `project_constraint`.
- **`sp-test`**: Primary producer of reusable testing `workflow_gap`, testing-specific `project_constraint`, and reusable `pitfall` findings about the project test surface.
- **`sp-implement`**: Primary producer of `pitfall`, `recovery_path`, and `project_constraint`.
- **`sp-debug`**: Primary producer of `pitfall`, `recovery_path`, and repeated debugging-side `project_constraint`.
- **`sp-fast`**: Strong consumer, weak producer (only produces clearly high-signal findings).
- **`sp-quick`**: Strong consumer, selective producer (only for reusable findings).
- **`sp-map-codebase`**: Primary producer of brownfield `project_constraint` and mapping-related `workflow_gap`.

**CLI Learning Commands:**
Use the `specify learning` CLI to manage the learning state explicitly:
- `specify learning status`: Inspect learning file state.
- `specify learning start --command <command-name>`: Prepare learning context. Use the
  workflow name without the `sp-` prefix.
- `specify learning capture --command <command-name> --type <type> --summary "<summary>" --evidence "<evidence>"`: Capture a candidate learning for the active workflow.
- `specify learning capture-auto --command <command-name> ...`: Infer candidate learnings from workflow state files when the workflow has a durable state surface such as `implement-tracker.md`, quick `STATUS.md`, or debug session files.
- `specify learning promote --recurrence-key <key> --target <learning|rule>`: Promote a learning into `project-learnings.md` or `project-rules.md`.

**First-Party Learning Hooks:**
Use the `specify hook` surface when a workflow needs product-level enforcement instead of prompt-only discipline:
- `specify hook signal-learning --command <command-name> ...`: Compute a friction-based pain score during the run. It warns when retry attempts, hypothesis changes, validation failures, route changes, false starts, or hidden dependencies indicate reusable learning value.
- `specify hook review-learning --command <command-name> --terminal-status <resolved|blocked> ...`: Required before terminal closeout. It may record `--decision none --rationale "..."`, but terminal workflows should not skip the review gate.
- `specify hook capture-learning --command <command-name> --type <type> --summary "..." --evidence "..."`: Capture structured path learning with optional `--pain-score`, `--false-start`, `--rejected-path`, `--decisive-signal`, `--root-cause-family`, `--injection-target`, and `--promotion-hint`.
- `specify hook inject-learning --command <command-name> --type <type> --summary "..."`: Derive the workflow, document, or rule surfaces where the learning should be injected so future runs are stopped earlier.

`signal-learning` is a soft prompt. `review-learning` is the hard terminal gate. `capture-learning` is the structured candidate writer. `inject-learning` is the prevention-routing helper. Promotion still requires recurrence or explicit confirmation.

## Learning-Start Trigger Matrix

- **`sp-specify`**: Run `specify learning start --command specify --format json`
  before request shaping, discovery, or spec framing begins.
- **`sp-plan`**: Run `specify learning start --command plan --format json` before
  decomposition, sequencing, or plan shaping begins.
- **`sp-checklist`**: Run `specify learning start --command checklist --format json`
  before checklist shaping, review-scope selection, or requirement-quality analysis begins.
- **`sp-tasks`**: Run `specify learning start --command tasks --format json` before
  task-batch generation or task-shaping begins.
- **`sp-test`**: Run `specify learning start --command test --format json` before
  testing-system inventory, framework adoption, or testing-contract generation begins.
- **`sp-implement`**: Run `specify learning start --command implement --format json`
  before editing, delegation, or implementation verification begins.
- **`sp-debug`**: Run `specify learning start --command debug --format json` before
  repro, investigation, or root-cause analysis begins.
- **`sp-fast`**: Run `specify learning start --command fast --format json`
  immediately after the task stays on the fast lane and before execution begins.
- **`sp-quick`**: Run `specify learning start --command quick --format json` before
  touched-area analysis, status initialization, or quick-task execution planning begins.
- **`sp-map-codebase`**: Run `specify learning start --command map-codebase --format json`
  before handbook/project-map refresh, coverage diagnosis, or brownfield map rebuild work begins.

## Learning-Capture Trigger Matrix

All workflows should run the learning review gate before final `resolved`, `blocked`, closeout, handoff, or completion reporting. If no reusable learning exists, use `specify hook review-learning --command <command> --terminal-status <status> --decision none --rationale "..."`. If reusable friction exists, capture it first with `specify hook capture-learning ...`, then review with `--decision captured`.

- **`sp-specify`**: Use `specify learning capture --command specify --type workflow_gap`
  when specification discovery exposes reusable missing requirements,
  `project_constraint`, or `user_preference`.
- **`sp-plan`**: Use `specify learning capture --command plan --type workflow_gap`
  when planning exposes reusable sequencing gaps, ownership gaps, or
  `project_constraint`.
- **`sp-checklist`**: Use `specify learning capture --command checklist --type workflow_gap`
  when checklist generation exposes reusable requirement-quality gaps, repeated ambiguity patterns, or
  checklist-shaping `project_constraint`.
- **`sp-tasks`**: Use `specify learning capture --command tasks --type workflow_gap`
  when task decomposition exposes reusable batching rules, dependency gaps, or
  execution-shaping `project_constraint`.
- **`sp-test`**: Use `specify learning capture --command test --type project_constraint`
  when testing bootstrap or refresh exposes reusable framework rules, project-wide
  testing pitfalls, or contract-shaping `workflow_gap` findings.
- **`sp-implement`**: Prefer `specify implement closeout --feature-dir FEATURE_DIR`
  so implementation session state is validated and retry-heavy implementation
  patterns can be inferred from `implement-tracker.md` automatically. Fall back to
  `specify learning capture --command implement --type pitfall` when the durable
  state files do not capture the reusable insight.
- **`sp-debug`**: Prefer `specify learning capture-auto --command debug --session-file .planning/debug/[slug].md`
  so resolved debug sessions can infer repeatable failure and recovery patterns from
  the persisted session file. Fall back to `specify learning capture --command debug --type pitfall`
  when the durable state files do not capture the reusable insight.
- **`sp-fast`**: Use `specify learning capture --command fast --type pitfall` only for
  highest-signal `pitfall`, `workflow_gap`, or `project_constraint` findings that
  should survive beyond the fast-path session.
- **`sp-quick`**: Prefer `specify learning capture-auto --command quick --workspace .planning/quick/<id>-<slug>`
  so resolved quick tasks can infer retry-heavy patterns from `STATUS.md`.
  Fall back to `specify learning capture --command quick --type pitfall` for reusable
  `pitfall`, `recovery_path`, `workflow_gap`, or `project_constraint` findings that
  the quick-task state file does not capture on its own.
- **`sp-map-codebase`**: Use `specify learning capture --command map-codebase --type project_constraint`
  when mapping exposes reusable ownership rules, stale-handbook blind spots, or
  brownfield `workflow_gap` findings that other workflows must consume.

## How to Act on Learnings

1. **Consume First:** Always read `constitution.md`, `project-rules.md`, and `project-learnings.md` (in that order) before executing tasks, planning, or debugging. Do not rely on generic framework instincts if a project rule exists.
2. **Identify Candidates:** When you solve a difficult bug, receive a global preference correction from the user, or notice a gap in the provided plan, recognize it as a candidate learning.
3. **Capture:** Do not silently adapt your local behavior without recording it for the future. Prefer `specify hook capture-learning` for structured path learning; use `specify learning capture` only as the lower-level fallback.
4. **Promote:** Do not immediately write stable non-principle rules into `constitution.md`. 
   - New observations go to `candidates.md`.
   - Repeated/confirmed observations go to `project-learnings.md` (via `specify learning promote --target learning`).
   - True stable cross-workflow rules go to `project-rules.md` (via `specify learning promote --target rule`).

## Behavioral Rules

- **Do NOT** automatically edit `constitution.md` for a single-task bug fix or minor user preference.
- **Do NOT** trap valuable cross-stage learnings inside single-task memory (like `alignment.md` or chat history). Extract them to the candidate layer.
- **Do NOT** close a terminal `sp-*` workflow without either a captured learning or an explicit `review-learning --decision none` rationale.
- Keep `project-rules.md` stricter than `project-learnings.md`.
