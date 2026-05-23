# Fast Full-Fidelity Map Update Design

**Date:** 2026-05-22
**Status:** Approved direction; review updates applied
**Owner:** Codex

## Summary

This design changes project cognition maintenance from a heavy workflow detour
into a fast full-fidelity incremental update path.

"Lightweight" in this design does not mean small, weak, or metadata-only. It
means the system updates the project cognition map as completely as possible at
the lowest practical cost:

- no full repository rescan for ordinary maintenance
- no full graph rebuild when a usable baseline exists
- no reliance on final chat memory after context compression
- no user cleanup burden in the common case
- no loss of graph semantics such as owners, consumers, generated surfaces,
  verification routes, confidence, known unknowns, and minimal live reads

The approved direction is a commit-first, journal-backed, bounded-live-read
incremental engine:

1. Workflows open a durable delta session when source-changing work begins.
2. Leaders, phases, and subagents append small map-delta records as work
   progresses.
3. When verification passes, workflows create a task-scoped commit by default
   when git is available, the active workflow is source-changing, auto-commit is
   enabled, and the commit can be made safely.
4. Project cognition update uses the best available boundary in this order:
   task commit range, working-tree diff, delta journal paths.
5. The runtime merges git facts, delta journal semantics, existing graph closure,
   and bounded live reads into a transactional graph patch.
6. If the fast complete update cannot be fully proven, it records partial,
   review, known-unknown, and minimal-live-read state instead of escalating to a
   full scan/build.

`sp-map-update` remains the external maintenance command, but ordinary workflows
should call the same lower-level update engine directly during closeout. The
external workflow is reserved for explicit repair, review, or follow-up
maintenance, not for routine post-task refresh.

## Context

Project cognition currently has the right lifecycle direction:

- `sp-map-scan -> sp-map-build` creates the initial brownfield cognition
  baseline.
- `sp-map-update` maintains the baseline after ordinary changes.
- `project-cognition query` gives workflows task-local navigation inputs.

Recent guidance already says `map-update` should be preferred after a usable
baseline exists. However, the current implementation has a practical gap:

- workflow prompts describe a rich incremental update contract
- the Go runtime currently has only a minimal `project-cognition update` entry
  that records changed paths, looks up existing nodes, writes an update row, and
  marks status stale/review-oriented
- ordinary workflows can lose important update context across compaction,
  resumes, and subagent handoffs
- `sp-map-update` still feels heavy because too much semantic reconstruction is
  left to the workflow prompt instead of the runtime

The result is an awkward tradeoff. A metadata-only update is fast but not
complete. A full `sp-map-update` run is more complete but too slow and too
expensive to embed naturally into `sp-fast`, `sp-quick`, `sp-debug`,
`sp-tasks`, and `sp-implement`.

This design removes that tradeoff by making the runtime responsible for fast
full-fidelity incremental patching while workflows continuously provide the
semantic delta evidence the runtime cannot infer cheaply at the end.

## Problem

Waiting until final closeout to update project cognition is lossy.

A realistic task may span:

- multiple context windows
- multiple subagents
- debug or verification loops
- task tracker updates
- generated-surface propagation decisions
- test failures and repairs
- user-supplied constraints that are no longer visible in the final context

If the final updater sees only `git diff`, it knows which files changed but not
why they changed, what behavior surfaces moved, which consumers were checked,
which verification routes proved the update, or which uncertainties remain.

If the final updater relies on the agent to summarize all of that from memory,
it is fragile under compaction and subagent execution.

If every workflow routes through the full `sp-map-update` prompt, the update is
too heavy for routine use and starts to feel like an external chore.

The product need is:

- update the map by default after source-changing work
- keep the update as complete as the current evidence allows
- do it quickly
- avoid pushing cleanup or bookkeeping to the user

## Goals

- Treat "lightweight map update" as fast full-fidelity incremental maintenance,
  not weak or partial-by-default metadata recording.
- Capture map-relevant task semantics continuously during workflow execution so
  compaction and subagent boundaries do not lose update evidence.
- Prefer task-scoped git commits as the default update boundary when git is
  available, auto-commit is enabled, the active workflow is source-changing, and
  the commit can be made safely.
- Support projects without git and tasks that cannot safely commit by falling
  back to working-tree diff plus delta journal evidence.
- Keep user burden low: normal workflows should finish with source changes
  verified, task-scoped commit created when safe, and project cognition updated
  or cleanly marked partial/dirty.
- Prevent unrelated pre-existing user changes from entering task commits or
  cognition refresh commits.
- Make `project-cognition update` a runtime engine that can patch affected graph
  records, not merely mark status stale.
- Keep `sp-map-update` as an explicit external maintenance and repair command
  that uses the same runtime engine.
- Preserve `map-scan -> map-build` for first baseline creation and unusable
  baseline recovery only.

## Non-Goals

- Do not force every workflow to commit when git is absent, unavailable, or
  unsafe.
- Do not commit unrelated dirty work.
- Do not require users to manually stage files for ordinary successful flows.
- Do not make project cognition authoritative proof of source behavior. Live
  code, tests, scripts, config, or authoritative docs still prove technical
  claims.
- Do not collapse partial update results into false success.
- Do not redesign `sp-map-scan` or `sp-map-build` beyond preserving their
  existing role as baseline creation and structural recovery workflows.

## Approved Approach

Use a commit-first, journal-backed incremental update architecture.

The central principle is:

```text
Git identifies what changed.
Delta journals preserve why it changed and what was proven.
The existing graph identifies what the change may affect.
Bounded live reads fill only the gaps needed to patch the affected closure.
```

Ordinary source-changing workflows should not call the full `sp-map-update`
workflow as a heavy subroutine. They should call a lower-level runtime updater
that can consume the current delta session and produce one of these outcomes:

- `ready`: affected graph records were updated and validation passed
- `review`: graph records were updated, but bounded live review is still needed
  for some affected paths or claims
- `partial_refresh`: useful update data was recorded, but readiness did not pass
- `dirty`: the runtime could not update now, but the exact task scope is
  recorded for later `sp-map-update`
- `needs_rebuild`: only for missing/unusable baseline, schema failure, zero
  active-generation path index, explicit rebuild request, or proven baseline
  identity invalidation

The user experience should be boring in the common case:

```text
workflow runs
verification passes
task-scoped commit is created when safe
project cognition is updated from that commit and delta journal
the final report includes the commit id and map refresh outcome
```

When the clean path cannot be followed, the system degrades automatically and
truthfully instead of handing routine cleanup to the user.

## Workflow Lifecycle

### Start

When a workflow may change source/runtime truth, it opens a delta session:

```text
project-cognition delta begin --origin-command quick --format json
```

The session records:

- session id
- origin command
- current branch
- base commit when git exists
- initial dirty paths
- whether the worktree was clean at start
- active feature, quick-task, debug-session, or implementation tracker path when
  available

The initial dirty snapshot is important. It lets closeout distinguish user
pre-existing dirty work from files changed by the current workflow.

### During Work

Each material phase, subagent handoff, join point, verification step, or
recovery step can append a compact map-delta record:

```text
project-cognition delta append --session <id> --packet-file <json>
```

Append points should be cheap. They should not require a map update. They only
record durable facts while they are still fresh.

### Closeout

After verification passes, the workflow asks the runtime to finalize:

```text
project-cognition update --delta-session <id> --mode workflow-finalize --format json
```

The updater chooses the best boundary:

1. A safe task-scoped commit created by the workflow.
2. A user-created commit within the delta session's base/head boundary.
3. Working-tree diff from the recorded base.
4. Delta journal changed paths.

The workflow then reports:

- changed code paths
- changed behavior surfaces
- verification evidence
- task commit id when present
- project cognition update id
- refresh outcome
- remaining review or dirty scope when any

## Delta Journal Contract

Delta records must be small, append-only, and safe to write frequently.

A delta session should live under:

```text
.specify/project-cognition/delta-sessions/<session-id>/
  session.json
  events/*.json
  summary.json
```

The exact storage can evolve, but the contract should include these fields.

### Session Fields

```json
{
  "session_id": "delta-20260522T120000Z-quick-login",
  "origin_command": "quick",
  "origin_context": {
    "feature_dir": ".specify/features/001-demo",
    "quick_task_dir": ".planning/quick/123-demo",
    "debug_session": ".planning/debug/login.md",
    "lane_id": "lane-1"
  },
  "git": {
    "available": true,
    "base_commit": "abc123",
    "branch": "main",
    "initial_dirty_paths": []
  },
  "created_at": "2026-05-22T12:00:00Z"
}
```

### Event Fields

Each event should support:

- `event_id`
- `session_id`
- `event_type`
- `origin_command`
- `origin_lane_id`
- `phase`
- `changed_paths`
- `read_paths`
- `behavior_surfaces`
- `graph_semantics`
- `verification_evidence`
- `generated_surface_notes`
- `owner_consumer_notes`
- `known_unknowns`
- `confidence`
- `created_at`

`graph_semantics` should allow structured facts such as:

- owner changed
- consumer checked
- verification route added or changed
- alias or route phrase changed
- generated output source changed
- state surface changed
- command/API/config contract changed
- destructive or lifecycle behavior changed

Events are evidence hints. The runtime must still validate against git facts,
existing graph state, and bounded live reads before publishing strong claims.

## Commit-First Boundary Policy

Git commit is the preferred update boundary when available because it gives the
runtime an exact source-change set and a stable content snapshot.

### Auto-Commit Default

Task-scoped auto-commit is default-on for source-changing workflow closeout, but
only after verification has passed, or when the workflow is intentionally
committing a documented blocked/partial artifact state, and only when the safety
checks in this section pass.

Auto-commit is not a global instruction to commit every workflow. It is gated by
all of these conditions:

- the workflow changed source, runtime, tests, docs, templates, config, or other
  committed truth-owning surfaces
- git is available and the repository has a base commit
- the workflow has a delta session or equivalent durable changed-path record
- verification for the workflow's done condition has passed, or the workflow is
  intentionally committing a documented blocked/partial artifact state
- workflow-owned paths can be computed without ambiguity
- commit hooks, commit-message policy, and repository policy allow the commit

Auto-commit is disabled when either of these is true:

- `.specify/config.json` contains:

  ```json
  {
    "project_cognition": {
      "auto_commit": false
    }
  }
  ```

- `SPECIFY_PROJECT_COGNITION_AUTO_COMMIT=0` is set for the current process.

The config setting is the project-wide default. The environment variable is a
session override. A workflow may still recommend a manual commit when
auto-commit is disabled, but it must not create one.

### Task Commit Rules

After workflow verification passes, the workflow should create a task commit
when all of these are true:

- git is available
- the repository has a base commit
- auto-commit is enabled
- the workflow can identify its changed paths
- unrelated pre-existing dirty paths can be excluded
- verification has passed or the workflow is intentionally committing a
  documented blocked/partial state
- staging only the workflow-owned paths is safe

The workflow must not stage the whole worktree by default.

It should stage only paths in the workflow-owned set:

- changed code paths
- changed tests
- changed docs/config/templates needed for the task
- workflow artifacts explicitly owned by the task when they are meant to be
  committed

It must not include:

- unrelated dirty paths present before the delta session
- secret or credential files
- editor/temp/cache files
- project cognition runtime metadata generated by the later map update

### Workflow-Owned Path Computation

The workflow-owned path set must be computed from durable evidence, not from
final narration.

Start with the union of:

- delta session `changed_paths`
- accepted worker result `changed_code_paths`
- accepted worker result write scopes that actually changed on disk
- workflow leader changes recorded in the active tracker or summary artifact
- explicit workflow artifacts that the workflow contract says are committed
  outputs, such as a quick-task `SUMMARY.md`, a debug session file, an
  implementation tracker, or feature artifacts when they belong to the current
  run
- files added, deleted, renamed, or modified between `base_commit` and the
  candidate task commit boundary when git can prove they were created during
  this workflow session

Then subtract:

- paths present in the delta session's initial dirty snapshot
- paths matched by `.gitignore`, `.cognitionignore`, generated cache ignores, or
  repository secret/credential deny lists
- project cognition metadata produced after the task commit boundary
- unrelated files not mentioned by the delta session, accepted worker results,
  or explicit workflow artifact contract

An initially dirty path may be included only when the workflow intentionally
claims that same path, records the claim in the delta session, and performs a
conflict check:

- compare the initial dirty snapshot to the current content or diff
- prove the path is part of the current task's accepted write scope
- record that the workflow is taking ownership of the path for this commit
- if the path contains user changes that cannot be separated from task changes,
  do not auto-commit that path

If any path remains ambiguous after this computation, auto-commit is skipped and
the updater falls back to working-tree diff plus delta journal evidence.

If the task-scoped commit succeeds, `project-cognition update` uses:

```text
base_commit..task_commit
```

as the authoritative changed-path boundary.

### Cognition Metadata Commit Rules

Project cognition update output should not be mixed into the task commit.

Project cognition metadata has two persistence classes:

- **Tracked runtime state:** files that the project policy explicitly commits,
  typically `.specify/project-cognition/status.json`,
  `.specify/project-cognition/project-cognition.db`, and accepted update
  metadata when those paths are not ignored.
- **Local workbench state:** delta sessions, transient event logs, workbench
  packets, temporary validation output, and local cache files. These are local
  unless a repository policy explicitly says otherwise.

The updater must check repository ignore rules and project policy before
attempting a metadata commit. If `.specify/project-cognition/**` is ignored, or
if project policy marks cognition runtime state as local-only, skip the metadata
commit and report the persisted local refresh state instead.

If project cognition metadata is meant to be committed and it is safe to do so,
create a separate commit:

```text
chore: update project cognition
```

This commit should contain only cognition runtime metadata and accepted update
artifacts.

If a safe metadata commit cannot be made, leave the cognition changes in the
working tree and report the exact state. Do not contaminate the task commit.

### Fallback Rules

If a safe task commit cannot be created:

- use working-tree diff when git exists
- use delta journal changed paths when git does not exist
- mark dirty/partial when even the delta evidence is insufficient

Fallback is automatic. The user should not be asked to fix routine commit
preconditions during a normal workflow closeout.

## Incremental Update Engine

The lower-level updater should be implemented as a runtime engine behind both
ordinary workflow closeout and `sp-map-update`.

Inputs:

- commit range or working-tree diff
- delta session events
- explicit changed paths
- user supplements when present
- current `status.json`
- current `project-cognition.db`

Outputs:

- updated `project-cognition.db`
- updated `status.json`
- update event row
- refresh outcome
- minimal live reads for any remaining review state

### Boundary Selection

The updater resolves the changed-path boundary in this priority order:

1. `--commit-range <base>..<head>`
2. `--delta-session` task commit metadata
3. git diff from session base to current worktree
4. explicit `--changed-path`
5. delta event changed paths

All paths are normalized and filtered through `.cognitionignore`.

### Evidence Merge

For each changed path, the updater merges:

- git change kind: added, modified, deleted, renamed
- content hash before/after when available
- delta events mentioning the path
- verification evidence from the workflow
- prior path index rows
- owner/consumer edges reachable from the current graph
- aliases, query examples, test routes, generated surfaces, and claims attached
  to the affected closure

### Bounded Live Reads

The updater may perform bounded live reads when needed to preserve fidelity.

Allowed bounded reads include:

- changed files
- nearest local imports or direct dependency files
- related tests from `test_index` or delta events
- generated source templates that directly produced changed generated surfaces
- docs or command templates explicitly linked in the existing graph or delta
  journal
- small callsite sets discovered through indexed graph edges or targeted search

Disallowed default reads:

- full repository scan
- broad unrelated top-level directory traversal
- raw graph export rewrites
- `.specify/**` as graph evidence except project cognition control artifacts
  needed to operate the updater
- `.cognitionignore`-excluded paths

The live-read budget is measured by all of these units:

- file count
- total bytes read
- targeted search calls
- elapsed time

The default workflow-finalize budget is:

- 25 files
- 1 MiB total file content
- 20 targeted search calls
- 10 seconds wall-clock time

The default explicit `sp-map-update` budget is larger because it is an external
maintenance command:

- 100 files
- 5 MiB total file content
- 80 targeted search calls
- 60 seconds wall-clock time

Budgets should be configurable through `.specify/config.json`:

```json
{
  "project_cognition": {
    "update_live_read_budget": {
      "workflow_finalize": {
        "files": 25,
        "bytes": 1048576,
        "search_calls": 20,
        "elapsed_ms": 10000
      },
      "map_update": {
        "files": 100,
        "bytes": 5242880,
        "search_calls": 80,
        "elapsed_ms": 60000
      }
    }
  }
}
```

Every update result must report the budget configured, the budget consumed, and
whether the result was limited by budget. When the budget is not enough, record
`review` or `partial_refresh` with `minimal_live_reads` instead of escalating to
scan/build.

### Patch Algorithm

At a high level:

```text
BEGIN IMMEDIATE
  resolve active generation
  resolve changed paths
  load delta events
  lookup path_index for changed paths
  provisionally adopt localized new paths when safe
  compute affected closure through owners, consumers, generated surfaces,
    state surfaces, verification routes, aliases, claims, conflicts, and slices
  refresh evidence rows for changed paths
  upsert or invalidate affected path, symbol, entrypoint, alias, test, and
    verification indexes
  update affected nodes and edges
  update claims backed by changed evidence
  mark unproven claims stale or low confidence
  update conflicts and known unknowns
  recompute affected route packs and query examples
  insert update event
  run readiness checks for affected closure
COMMIT
```

If a strong update cannot be proven, the transaction should still publish safe
partial information when possible:

- low-confidence facts
- stale markers
- known unknowns
- minimal live reads
- review paths
- affected closure metadata

If database integrity would be harmed, roll back and record a failed update
attempt separately.

## Required Runtime Data Model

The current Go runtime schema is too small for full-fidelity incremental
maintenance. The updater needs graph tables and indexes that match the SQLite
graph-store design direction.

At minimum, implementation should add or complete:

- `generations`
- `evidence`
- `nodes`
- `edges`
- `claims`
- `conflicts`
- `path_index`
- `symbol_index`
- `alias_index`
- `entrypoint_index`
- `test_index`
- `slice_members`
- `updates` with result state and attrs JSON
- `delta_sessions`
- `delta_events`

The update engine depends most heavily on:

- `path_index` to resolve changed paths into graph nodes
- typed edges to find owners, consumers, generated surfaces, and verification
  routes
- claims and evidence links to invalidate or refresh stale facts
- alias/query-example indexes to keep natural-language routing current
- update events to explain what was changed and why

## Workflow Integration

### `sp-fast`

`sp-fast` should use the delta session only for source-changing tasks that may
affect project cognition. It remains leader-direct.

Closeout behavior:

- append final changed paths and verification evidence
- create a safe task commit when auto-commit is enabled and all commit gates pass
- call runtime update
- if update is partial/dirty, report it without failing the fast task

### `sp-quick`

`sp-quick` should create the delta session after quick-task workspace
initialization and carry the session id in `STATUS.md`.

Subagent results should include map-delta payloads when they touched source,
tests, docs, templates, config, runtime behavior, or verification routes.

Closeout behavior:

- merge quick-task summary, worker results, and delta events
- create a task commit from tracked changed paths when auto-commit is enabled
  and all commit gates pass
- call runtime update
- write refresh outcome into `SUMMARY.md`

### `sp-debug`

`sp-debug` should append map deltas during investigation and fixing:

- confirmed root cause owner
- rejected surface fixes
- changed control/observation state surfaces
- repro and regression verification
- adjacent risk targets reviewed

If the debug fix is verified, the runtime update should happen before moving to
resolved or awaiting human verification when safe. If the updater is partial,
the debug session should preserve that map state without blocking verified
source fix reporting.

### `sp-tasks`

`sp-tasks` is usually planning/artifact work, not source runtime truth. It
should not start a source delta session by default.

If task generation changes workflow/runtime truth surfaces, command templates,
or generated behavior contracts, it may open a delta session and update
cognition like other workflows.

### `sp-implement`

`sp-implement` should carry one delta session across batches for a feature
implementation run.

Each accepted worker handoff should include:

- changed paths
- read paths that materially informed the change
- behavior surfaces changed
- verification routes added or run
- map-relevant unknowns

At final closeout or at major feature milestones, `sp-implement` should attempt
task-scoped commits and run the update engine. For long-running implementations,
the workflow may also run intermediate update checkpoints after accepted
commits so a future resume starts from current cognition.

## `sp-map-update` Role

`sp-map-update` should become the explicit external wrapper around the same
runtime update engine.

Use it when:

- a prior workflow recorded partial/dirty map state
- the user explicitly asks to refresh cognition
- the runtime reports `needs_update`
- a workflow did not have enough context or permission to finalize map refresh
- manual supplement or correction is needed

It should not duplicate the full semantic algorithm in prompt prose. The prompt
should prepare inputs, call the runtime engine, inspect the result, and handle
review/partial outcomes.

## Cleanliness Rules

The design must keep the user's workspace clean.

Rules:

- Do not stage all changes.
- Do not commit unrelated pre-existing dirty work.
- Do not mix task changes and project cognition metadata in the same commit.
- Do not commit secrets, ignored files, editor files, cache files, or build
  outputs.
- Do not fail a verified source task only because cognition update could not be
  fully finalized.
- Do not require user decisions for routine fallback from commit range to
  working-tree diff or delta journal.
- Do not create scan/build follow-up chores for ordinary existing-baseline
  uncertainty.

User intervention is appropriate only when:

- the workflow cannot distinguish task-owned changes from user-owned changes
- git hooks or policy intentionally reject the commit
- git identity or permissions are unavailable and the project requires commits
- the user must choose between ambiguous project cognition candidates
- the next action is destructive or would rewrite user work

## Failure Modes And Outcomes

### Ready

The updater patched affected graph records and readiness checks passed.

Status:

- freshness may be `fresh`
- readiness is query-ready or ready-equivalent
- final report says map refresh completed

### Review

The updater patched safe records but needs targeted live review for some
closure facts.

Status:

- freshness may be `possibly_stale`
- readiness is `review`
- final report includes `minimal_live_reads`

### Partial Refresh

The updater recorded useful data, but readiness did not pass.

Status:

- freshness is `partial_refresh`
- recommended action is `run_map_update`
- final report must not claim complete refresh

### Dirty

The updater could not run or could not safely write, but it preserved exact
scope for later.

Status:

- dirty state includes origin command, feature/task/session, lane id, and paths
- recommended action is `run_map_update`

### Needs Rebuild

Allowed only for:

- missing baseline
- unusable DB/status/schema
- zero active-generation path-index rows
- explicit rebuild request
- proven baseline identity invalidation

Ordinary uncertainty, new files, weak ownership, or large changed-path batches
must not produce this outcome by themselves.

## Implementation Surface

This design affects shared product surfaces, not one command template.

Likely implementation surfaces include:

- `tools/project-cognition/internal/update/**`
- `tools/project-cognition/internal/store/**`
- `tools/project-cognition/internal/query/**`
- `tools/project-cognition/internal/runtime/**`
- `tools/project-cognition/internal/validation/**`
- `tools/project-cognition/internal/cli/cli.go`
- `templates/commands/{fast,quick,debug,tasks,implement,map-update}.md`
- `templates/command-partials/common/**`
- `templates/worker-prompts/**`
- `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`
- `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`
- `templates/passive-skills/subagent-driven-development/SKILL.md`
- `src/specify_cli/execution/**`
- `src/specify_cli/hooks/project_cognition.py`
- `src/specify_cli/hooks/artifact_validation.py`
- `src/specify_cli/integrations/base.py`
- `src/specify_cli/integrations/**`
- `README.md`
- `PROJECT-HANDBOOK.md`
- regression tests under `tests/` and `tools/project-cognition/internal/**`

The exact implementation can be staged, but no stage should claim fast
full-fidelity map update until the runtime can write graph patches, not only
status metadata.

## Staged Delivery Contract

Implementation may ship in phases, but each phase must expose only the outcome
labels it can truthfully support. This prevents early slices from advertising
full-fidelity update before the graph patch engine exists.

### Phase 1: Delta Journal

Capabilities:

- `project-cognition delta begin`
- `project-cognition delta append`
- durable delta session storage
- workflow/subagent payload shape
- status/report plumbing for recorded delta sessions

Allowed outcomes:

- `dirty`
- `recorded_delta`

Forbidden claims:

- no `ready`
- no `review`
- no `partial_refresh`
- no claim that graph records were patched

### Phase 2: Safe Boundary Selection

Capabilities:

- git base/head detection
- initial dirty snapshot
- workflow-owned path computation
- safe task-scoped commit attempt
- fallback to working-tree diff or delta journal
- no graph mutation beyond existing status/update metadata

Allowed outcomes:

- `dirty`
- `recorded_delta`
- `boundary_resolved`
- `commit_created`
- `commit_skipped`

Forbidden claims:

- no `ready`
- no `review`
- no `partial_refresh`
- no claim that the cognition graph is updated

### Phase 3: DB Graph Patch MVP

Capabilities:

- required graph/index schema exists
- update engine resolves changed paths through `path_index`
- bounded live reads are enforced and reported
- affected evidence, path index rows, claims, known unknowns, and update events
  can be patched transactionally for localized changes

Allowed outcomes:

- `ready`
- `review`
- `partial_refresh`
- `dirty`
- `needs_rebuild` only for the explicit rebuild conditions

Required limitation:

- `ready` may be reported only for changed paths whose affected closure was
  fully patched and validated by the MVP graph tables.

### Phase 4: Workflow Integration

Capabilities:

- `sp-fast`, `sp-quick`, `sp-debug`, and `sp-implement` create or resume delta
  sessions
- worker prompts can return map-delta payloads
- workflow closeout attempts safe task commits when enabled
- workflow closeout invokes the runtime update engine
- summaries report commit and refresh outcomes

Allowed outcomes:

- same as Phase 3

Required limitation:

- workflows must surface Phase 1 or Phase 2 labels directly when the runtime has
  not reached Phase 3. They must not translate `recorded_delta` or
  `boundary_resolved` into `ready`.

### Phase 5: External `sp-map-update` Wrapper

Capabilities:

- `sp-map-update` prepares supplemental inputs
- calls the same runtime update engine
- handles review/partial/dirty states
- avoids duplicating graph patch logic in prompt prose

Allowed outcomes:

- same as Phase 3

Acceptance for the whole feature:

- only after Phase 5 may documentation describe the product as delivering fast
  full-fidelity map update end to end.

## Testing Strategy

Runtime tests should cover:

- delta session begin/append/finalize
- delta journal survives simulated context compression by using only disk state
- task commit boundary is preferred over working-tree diff
- unrelated initial dirty paths are excluded from task commits
- commit failure falls back to diff/journal without losing update scope
- changed paths are filtered through `.cognitionignore`
- updated path index rows for added files
- affected closure traversal through owners, consumers, generated surfaces, and
  verification routes
- claim invalidation when backing evidence changes
- alias/query-example refresh when command or route language changes
- partial/review outcomes preserve known unknowns and minimal live reads
- ordinary large changed-path batches do not route to scan/build
- missing/unusable baseline still routes to scan/build

Workflow/template tests should cover:

- `sp-fast`, `sp-quick`, `sp-debug`, and `sp-implement` mention delta sessions
  and closeout update behavior consistently
- generated worker prompts can return map-delta payloads
- quick/debug/implement summaries include project cognition refresh outcome
- task commit and cognition metadata commit are described as separate commits
- no prompt tells agents to stage all changes
- no prompt routes ordinary existing-baseline uncertainty to scan/build

Git safety tests should cover:

- clean worktree task commit
- pre-existing unrelated dirty file
- task-owned plus user-owned overlapping file path conflict
- missing git
- git identity failure
- hook failure
- metadata commit safety
- staged delivery labels do not overclaim before Phase 3 graph patch support
- live-read budget limits by files, bytes, search calls, and elapsed time
- metadata commit is skipped when `.specify/project-cognition/**` is ignored or
  project policy marks it local-only

## Acceptance Criteria

- Ordinary source-changing workflows open or resume a delta session and preserve
  map-relevant evidence outside chat memory.
- Subagent handoffs can contribute map-delta payloads.
- Workflow closeout creates a task-scoped commit by default when git is
  available, auto-commit is enabled, and all safety gates pass.
- Auto-commit is default-on for source-changing workflow closeout but can be
  disabled by `.specify/config.json` or
  `SPECIFY_PROJECT_COGNITION_AUTO_COMMIT=0`.
- Workflow-owned paths are computed from delta sessions, accepted worker
  outputs, explicit workflow artifacts, and git evidence, while excluding
  unrelated initial dirty paths unless they are intentionally claimed and
  conflict-checked.
- The task commit contains only workflow-owned files.
- Project cognition metadata is not mixed into the task commit.
- Project cognition metadata commits are skipped when the runtime paths are
  ignored or project policy marks them local-only.
- If task commit cannot be safely created, update falls back automatically to
  working-tree diff plus delta journal.
- `project-cognition update` can consume a delta session and produce ready,
  review, partial, dirty, or needs-rebuild outcomes.
- Before graph patch support exists, staged delivery labels cannot claim ready,
  review, partial refresh, or full-fidelity map update.
- Update results report live-read budget configuration, consumption, and
  budget-limited status.
- Ready/review/partial updates patch graph records, not only `status.json`.
- Ordinary existing-baseline uncertainty never routes to scan/build by itself.
- Final reports include commit boundary and map refresh outcome without asking
  the user for routine cleanup.
- `sp-map-update` uses the same runtime engine as workflow closeout.
- Tests prove user-owned dirty work is not committed or overwritten.

## Risks And Mitigations

Risk: Auto-commit behavior may surprise users.

Mitigation: Commit only after verification or an intentional documented
blocked/partial artifact decision, only from tracked workflow-owned paths, and
never include unrelated initial dirty work. Fall back instead of forcing a
commit when the safe boundary is unclear.

Risk: Delta journals may become noisy.

Mitigation: Keep events compact and structured. Store only paths, surfaces,
verification evidence, semantics, and uncertainty needed for map update.

Risk: The runtime may under-update graph semantics when relying on bounded live
reads.

Mitigation: Use existing graph closure and delta semantics first, then bounded
reads. Record review/partial state with minimal live reads when the proof is
insufficient.

Risk: Workflows may treat project cognition update success as proof that code
works.

Mitigation: Keep verification evidence separate. Project cognition supports
navigation and maintenance; source behavior is proven by live code and checks.

Risk: Implementing the full graph patch engine is larger than prompt updates.

Mitigation: Stage the work: delta journal and safe boundary first, then graph
patch schema/indexes, then workflow closeout integration. Do not claim the full
product outcome until all pieces are present.

## Decision

Proceed with a fast full-fidelity map update design based on durable delta
journals, commit-first boundaries, safe fallback to diff/journal, bounded live
reads, transactional graph patches, and clean separation between task commits
and project cognition metadata commits.
