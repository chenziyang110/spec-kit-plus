# Workflow State: [FEATURE NAME]

## Current Command

- active_command: `[canonical sp-* command, e.g. sp-specify or sp-prd]`
- status: `active | blocked | completed`

## Phase Mode

- phase_mode: `planning-only | research-only | design-only | task-generation-only | analysis-only | execution-only`
- summary: [One-sentence reminder of what this phase is allowed to do]

## Scenario Profile

- active_profile: [scenario profile selected for this workflow]
- routing_reason: [why this scenario profile was selected]
- confidence_level: `low | medium | high`

## Profile Obligations

- required_sections:
  - [artifact section required by the active profile]
- activated_gates:
  - [quality gate activated by the active profile]
- task_shaping_rules:
  - [rule that must shape downstream task generation or execution]
- required_evidence:
  - [evidence required before the workflow can transition]
- transition_policy: [handoff or phase-transition policy required by the active profile]

## Allowed Artifact Writes

- [artifact path the current command may update]

## Forbidden Actions

- [source-code or execution action that must not happen in this phase]

## Authoritative Files

- [artifact that must be re-read on resume before continuing]

## Lane Context

- lane_id: [stable lane identifier for this feature workflow]
- branch_name: [branch bound to this lane]
- worktree_path: [isolated worktree bound to this lane]
- recovery_state: `resumable | uncertain | blocked | completed`
- last_stable_checkpoint: [most recent durable resume point]

## Atlas Read Evidence

- atlas_read_completed: `true | false`
- atlas_paths_read:
  - [atlas artifact actually read before source-level work]
- atlas_root_topics_read:
  - [root topic file actually read]
- atlas_module_docs_read:
  - [module overview or module-local doc actually read]
- atlas_status_basis: [fresh | missing | stale | possibly_stale plus the decision taken]
- atlas_blocked_reason: [why atlas gating blocked work, if it did]

## Resume Checklist

- Re-read this file first after compaction or session recovery.
- Re-read the authoritative files before taking the next step.
- draft_file: `specify-draft.md`
- coverage_mode: `core | full`
- observer_status: `not-run | pending | completed | blocked`
- last_observer_pass: `global-entry | capability-closure | final-handoff`
- If the next action conflicts with the current `phase_mode`, stop and repair the workflow state instead of improvising.
- Native hook recovery may redirect the first phase jump back to this state; repeated or explicit phase jumps must be blocked by workflow policy.

## Exit Criteria

- [Condition that makes the current phase complete]

## Next Action

- [Smallest next step to take from the current phase]

## Next Command

- `/sp.constitution | /sp.prd | /sp.plan | /sp.tasks | /sp.analyze | /sp.implement | /sp.clarify | /sp.deep-research`

## Learning Signals

- route_reason: [Why the current workflow phase must hand off, reopen, or stop]
- blocked_reason: [What specifically prevented clean completion]

### False Starts

- [Misleading early route, assumption, or diagnosis that later proved wrong]

### Hidden Dependencies

- [Dependency, prerequisite, or external coupling discovered during the workflow]

### Reusable Constraints

- [Constraint that future related work should see before repeating the same mistake]
