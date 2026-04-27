# Workflow State: [FEATURE NAME]

## Current Command

- active_command: `sp-specify`
- status: `active | blocked | completed`

## Phase Mode

- phase_mode: `planning-only | design-only | task-generation-only | analysis-only | execution-only`
- summary: [One-sentence reminder of what this phase is allowed to do]

## Allowed Artifact Writes

- [artifact path the current command may update]

## Forbidden Actions

- [source-code or execution action that must not happen in this phase]

## Authoritative Files

- [artifact that must be re-read on resume before continuing]

## Resume Checklist

- Re-read this file first after compaction or session recovery.
- Re-read the authoritative files before taking the next step.
- If the next action conflicts with the current `phase_mode`, stop and repair the workflow state instead of improvising.

## Exit Criteria

- [Condition that makes the current phase complete]

## Next Action

- [Smallest next step to take from the current phase]

## Next Command

- `/sp.constitution | /sp.plan | /sp.tasks | /sp.analyze | /sp.implement | /sp.spec-extend`
