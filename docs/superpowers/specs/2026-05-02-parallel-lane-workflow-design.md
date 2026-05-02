# Parallel Lane Workflow Design

Date: 2026-05-02
Status: Approved for implementation planning

## Goal

Support concurrent `sp-*` workflow execution for multiple independent features
without allowing those features to contaminate each other's state, code edits,
or recovery flow.

The target operator experience is:

- users continue invoking the existing root-level `sp-*` commands
- independent features execute in isolated lanes backed by distinct branches and
  worktrees
- workflow recovery remains available across `sp-specify`, `sp-plan`,
  `sp-tasks`, `sp-implement`, `sp-auto`, and other resumable `sp-*` commands
- crash, power-loss, or partial-write scenarios fail closed rather than
  auto-resuming the wrong lane

This design is intentionally scoped to the common case: multiple independent
requirements being developed in parallel. It does not attempt to make stacked
feature chains the default operating model.

## Problem Statement

Current workflow guidance assumes one active feature context at a time. That
works when branch name or current session history uniquely identifies the active
feature, but it breaks down when multiple independent requirements are being
developed concurrently and users continue working from the repository root.

The failure modes are:

- a root-level `sp-*` command guesses the wrong feature to resume
- `sp-auto` resumes "the latest" workflow even though multiple resumable lanes
  exist
- a power loss leaves workflow state half-written, but recovery logic trusts the
  stale state instead of reconciling against real artifacts
- two active requirements share one mutable workflow namespace and interfere
  with each other's `workflow-state.md`, `tasks.md`, `implement-tracker.md`, or
  related closeout artifacts
- branch/worktree isolation exists only informally instead of as a first-class
  workflow contract

The system therefore needs explicit concurrent lane modeling, safe recovery, and
an integration closeout path.

## Scope

This design covers:

- independent feature lanes with dedicated branch and worktree isolation
- root-level invocation of existing `sp-*` workflow commands
- resume/recovery behavior for resumable `sp-*` commands
- crash-consistent lane state recording
- lane discovery, reconcile, and safe command routing
- a dedicated closeout workflow for collecting completed lanes back into the
  mainline

This design does not make stacked feature development the primary model. Stacked
branches may be supported later, but the first release should optimize for
parallel, independent feature development.

## Primary Assumptions

- most concurrent work items are independent features, not dependency chains
- users commonly invoke `sp-*` commands from the repository root
- users do not want to manually manage or preselect lanes before every command
- resumability is a core product promise and must remain available
- correctness beats convenience when recovery is ambiguous

## Core Concepts

### Lane

A `lane` is the isolated execution unit for one independent feature workflow.

Each lane owns:

- one feature identity
- one feature directory
- one dedicated branch
- one dedicated worktree
- one workflow state lineage
- one recoverable execution history

The lane is the concurrency boundary. Parallelism is allowed across lanes, not
within one mutable lane state by multiple foreground workflows at once.

### Lane Registry

A repository-level lane registry provides discovery only. It is not the source
of truth for recoverability.

Suggested location:

- `.specify/lanes/index.json`

The registry should help answer:

- which lanes exist
- which feature each lane corresponds to
- which lane-local metadata directories exist
- which recent commands touched each lane

The registry may be stale and must be treated as rebuildable cache.

### Lane-Local Durable State

Each lane maintains its own durable metadata under a lane-local directory, for
example:

- `.specify/lanes/<lane-id>/lane.json`
- `.specify/lanes/<lane-id>/events.ndjson`
- `.specify/lanes/<lane-id>/lease.json`
- `.specify/lanes/<lane-id>/recovery.json`

These files support crash-safe replay and recovery decisions even if the global
index is stale or corrupt.

### Reconcile

`reconcile` is the required pre-recovery verification pass that reconstructs the
lane's true state from durable lane metadata and real feature artifacts before a
command is allowed to auto-resume.

The system must reconcile against:

- `workflow-state.md`
- `alignment.md`
- `context.md`
- `plan.md`
- `tasks.md`
- `implement-tracker.md`
- phase-plan files when present
- branch existence
- worktree existence
- lease freshness
- closeout / checkpoint evidence

Registry state may nominate candidates, but reconcile decides whether a lane is
actually resumable.

## State Model

Each lane should expose two different state dimensions.

### Lifecycle State

Lifecycle state represents where the feature is in the end-to-end workflow:

- `draft`
- `specified`
- `planned`
- `tasked`
- `implementing`
- `integrating`
- `completed`
- `abandoned`

This is the progress axis.

### Recovery State

Recovery state represents whether the lane is safe to continue:

- `resumable`
- `uncertain`
- `blocked`
- `completed`

This is the safety axis.

The separation is required because a lane may be in `implementing` lifecycle
state but still be `uncertain` after a crash.

## Crash Consistency and Recovery Safety

The system must assume that power loss, terminal kill, host crash, or partial
filesystem writes can leave workflow state inconsistent.

Therefore:

- the global lane registry is advisory only
- lease presence does not imply the workflow is still running
- the last recorded command does not imply the next safe action
- incomplete writes must bias toward `uncertain`, not optimistic resume

### Red Line

`uncertain` lanes must never be auto-resumed.

This applies to `sp-auto` and every resumable `sp-*` command.

### Recovery Classification

After reconcile, a lane must be classified as one of:

- `resumable`: safe to continue
- `uncertain`: conflicting or incomplete evidence; no automatic resume allowed
- `blocked`: missing prerequisites or required artifacts
- `completed`: lane is already finished

### Resumable Criteria

Typical `resumable` conditions include:

- the relevant stage artifacts exist and are parseable
- the latest stable checkpoint and current workflow stage agree
- branch and worktree still exist or can be deterministically recovered
- the lease is either actively renewed by a live session or has expired cleanly
  and the lane's next step can be inferred without ambiguity
- no required closeout record is missing for the last durable checkpoint

### Uncertain Criteria

Typical `uncertain` conditions include:

- lane metadata and feature artifacts disagree about current stage
- a lease expired without corresponding closeout or stable checkpoint
- `implement-tracker.md` indicates an open batch but the corresponding result or
  review closure is missing
- a branch or worktree reference exists in lane metadata but is missing or points
  somewhere inconsistent
- required state files are partially written, malformed, or mutually
  contradictory

### Blocked Criteria

Typical `blocked` conditions include:

- required stage artifacts are missing
- the lane exists but was never advanced to the command's prerequisite stage
- expected branch/worktree creation did not happen and cannot be reconstructed
  safely

## Lease Model

Each lane should support one foreground write lease at a time.

This means:

- two independent lanes may execute concurrently
- one lane may not have two simultaneous foreground `sp-*` commands mutating its
  state

Suggested durable lease fields:

- `session_id`
- `owner_command`
- `acquired_at`
- `renew_until`
- `repo_root`
- runtime token or equivalent liveness hint

Normal execution should:

1. acquire the lease
2. renew the lease while the command is active
3. write a stable closeout/checkpoint before exit
4. release the lease

Crash recovery should treat expired leases as evidence requiring reconcile, not
as proof that the lane can resume.

## Command Routing Model

Existing root-level `sp-*` commands remain the public operator surface.

Before any resumable `sp-*` command runs, it should go through a lane-resolution
step:

1. infer the command's recovery domain
2. discover candidate lanes from the registry
3. reconcile each candidate against lane-local and feature-local truth
4. decide whether to auto-resume, prompt minimally, or start new work

### Command-Semantic Candidate Filtering

Commands must filter candidates by command semantics, not by global recency.

Examples:

- `sp-plan` only considers lanes that can legitimately continue planning
- `sp-tasks` only considers lanes that can continue task generation
- `sp-implement` only considers implement-stage lanes
- `sp-auto` may consider cross-command candidates, but still must obey strict
  safety rules

This replaces "resume the most recent workflow" heuristics with
"resume the right workflow for this command" routing.

## Auto-Resume Rules

### Ordinary Resumable `sp-*` Commands

For commands like `sp-plan`, `sp-tasks`, `sp-implement`, and other resumable
workflow steps:

- if there is exactly one `resumable` candidate and no conflicting
  `uncertain` candidate in the relevant command domain, auto-resume it
- if there are multiple `resumable` candidates, do not guess; present a short
  selection list
- if any relevant candidate is `uncertain`, do not auto-resume
- if no `resumable` candidate exists, fall through to normal command start

### `sp-auto`

`sp-auto` should be the most conservative command because it spans multiple
workflow stages.

It may auto-resume only when all of the following are true:

- there is exactly one `resumable` candidate globally for the auto-routing
  domain
- there is no `uncertain` candidate that could conflict with the chosen lane
- the recommended next action is unambiguous
- stage prerequisites are intact

Otherwise `sp-auto` must stop and present a minimal user choice.

## New Work vs Resume

The system must not force the user to think in lane-management terms when they
are starting or resuming work from the repository root.

Recommended behavior:

### `sp-specify`

- if the invocation clearly provides new feature intent, default to creating a
  new lane
- if it does not clearly describe new feature intent and there is exactly one
  resumable `specify`-domain lane, resume it
- if both "new lane" and "resume existing lane" are plausible, present a short
  user choice

### Other Resumable `sp-*`

- attempt command-semantic resume first
- if exactly one safe candidate exists, resume it
- if the result is ambiguous, prompt minimally

This balances convenience with fail-closed recovery.

## Minimal Recovery UX

When user choice is required, the prompt should describe tasks in feature terms,
not internal lane identifiers.

Good prompt shape:

- `Continue implementing "parallel lane workflow"`
- `Continue planning "integration closeout workflow"`

Supplementary context may include:

- current stage
- last stable checkpoint
- `resumable` vs `uncertain`

Do not force the user to preselect or even understand a lane identifier before
ordinary root-level command use.

## Worktree and Branch Isolation

Each lane should own its own branch and worktree. This is not optional in the
parallel model.

The purpose is:

- isolate code edits
- isolate generated workflow artifacts and closeout state
- keep feature-local changes from polluting each other

The operator may still invoke commands from the repository root, but lane
resolution must bind execution to the selected lane's isolated branch/worktree
context under the hood.

Legacy branch-based "active feature" heuristics remain acceptable only when the
repository has a single active lane. Once parallel lanes exist, registry plus
reconcile becomes the authoritative routing model.

## `sp-integrate` Workflow

Parallel lane execution introduces a new need after implementation completes:
safe collection of independent lanes back into the mainline.

That concern should not be folded into `sp-implement`. It should become a
dedicated workflow named `sp-integrate`.

### Why `sp-integrate` Instead of `sp-merge`

The closeout step is not just a Git merge wrapper. It must also:

- discover completed or implementation-complete lanes
- verify that each lane is actually ready for integration
- detect drift from the target branch
- identify obvious overlap or ordering risk across candidate lanes
- manage lane lifecycle transition into and out of integration
- record integration completion and close the lane

`sp-integrate` is therefore a workflow orchestrator for lane closeout, not a
thin VCS alias.

### `sp-integrate` Responsibilities

`sp-integrate` should:

1. discover candidate lanes ready for integration
2. reconcile them against durable and feature-local truth
3. run integration prechecks
4. recommend independent vs ordered integration sequence
5. execute promote / sync-back / closeout actions appropriate to the runtime
6. mark the lane as integrated and completed

### Integration Preconditions

Integration readiness should include:

- no active conflicting lease
- required verification completed for the lane
- branch/worktree still coherent
- target branch drift evaluated
- obvious shared write-set or conflict hotspots surfaced

### First-Release Integration Model

The first release should optimize for independent lanes returning to `main`.

It should support:

- `sp-integrate` for discovery-driven closeout
- `sp-integrate --feature <feature>` for targeted lane closeout

It does not need to fully automate stacked branch orchestration in the first
release.

## Shared vs Integration-Specific Behavior

This lane model should be treated as a cross-CLI workflow improvement, not a
Codex-only behavior.

Shared behavior:

- lane registry semantics
- lane-local durable state
- reconcile rules
- resume safety rules
- `uncertain` auto-resume prohibition
- `sp-integrate` semantics

Integration-specific behavior may differ for:

- subagent dispatch surface
- team-runtime escalation
- worktree execution plumbing
- UI or prompt presentation details

## Rollout Plan

Implementation should proceed in three stages.

### Stage 1: Lane State and Recovery

Build:

- lane registry
- lane-local durable state
- reconcile classification
- lease handling
- command-semantic resume routing
- strict `sp-auto` safety

This stage solves the main correctness problem: concurrent lanes no longer
cross-resume each other.

### Stage 2: Branch/Worktree Automation

Build:

- automatic branch creation per lane
- automatic worktree creation per lane
- root-level command binding into lane isolation
- compatibility downgrade for legacy branch-only active-feature detection

This stage completes code isolation.

### Stage 3: `sp-integrate`

Build:

- integration discovery
- prechecks
- drift/conflict surfacing
- closeout recording
- lane completion / archival

This stage completes the end-to-end concurrent workflow lifecycle.

## Design Constraints

- keep the public daily workflow centered on existing `sp-*` commands
- do not require users to preselect lanes for ordinary root-level usage
- prefer automatic recovery only when it is unambiguous and safe
- fail closed when state is inconsistent
- preserve resumability as a workflow guarantee
- treat lane-local truth as authoritative over global registry cache
- treat crash consistency as a first-class requirement, not an edge case

## Acceptance Criteria

This design is successful when:

1. two independent features can run `sp-specify -> sp-plan -> sp-tasks ->
   sp-implement` concurrently without sharing mutable workflow state
2. each lane has distinct branch and worktree isolation
3. root-level `sp-*` commands can still resume work without forcing the user to
   manage lanes manually
4. the system never auto-resumes an `uncertain` lane
5. crash or power-loss scenarios are reconciled against real artifacts before
   resume
6. `sp-auto` only auto-resumes when there is one uniquely safe candidate
7. completed lanes can be collected through a dedicated `sp-integrate` closeout
   workflow

## Open Follow-Up Items

These items are intentionally deferred from the first implementation plan:

- stacked feature-chain orchestration as a first-class default
- advanced conflict prediction beyond precheck-grade overlap surfacing
- UI-specific presentation refinements beyond minimal command-line prompts
- cleanup or archival retention policy for old lane metadata after integration
