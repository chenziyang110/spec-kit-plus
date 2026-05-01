# Workflow State: [FEATURE NAME]

## Current Command

- active_command: `sp-specify`
- status: `active | blocked | completed`

## Phase Mode

- phase_mode: `planning-only | research-only | design-only | task-generation-only | analysis-only | execution-only`
- summary: [One-sentence reminder of what this phase is allowed to do]

## Allowed Artifact Writes

- [artifact path the current command may update]

## Forbidden Actions

- [source-code or execution action that must not happen in this phase]

## Authoritative Files

- [artifact that must be re-read on resume before continuing]

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
- If the next action conflicts with the current `phase_mode`, stop and repair the workflow state instead of improvising.

## Exit Criteria

- [Condition that makes the current phase complete]

## Next Action

- [Smallest next step to take from the current phase]

## Next Command

- `/sp.constitution | /sp.plan | /sp.tasks | /sp.analyze | /sp.implement | /sp.clarify | /sp.deep-research`

## Learning Signals

- route_reason: [Why the workflow must hand off or reopen instead of pretending it can continue locally]
- blocked_reason: [What specifically prevented clean completion]

### False Starts

- [Misleading early route, assumption, or diagnosis that later proved wrong]

### Hidden Dependencies

- [Dependency, prerequisite, or external coupling discovered during the workflow]

### Reusable Constraints

- [Constraint that future related work should see before repeating the same mistake]
