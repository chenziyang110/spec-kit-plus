# Workflow State: [FEATURE NAME]

## Current Command

- active_command: [sp-specify | sp-plan | sp-tasks | sp-implement | sp-debug | sp-analyze | sp-deep-research | sp-clarify | sp-constitution | sp-prd | sp-prd-scan | sp-prd-build]
- status: [active | completed | blocked]

## Phase Mode

- phase_mode: [planning-only | design-only | task-generation-only | execution-only | analysis-only | research-only]
- summary: [Short current-state summary for resume and hook context]

## Fixed Lifecycle State

- current_stage: [intent-analysis | intent-confirmation | question-batch | batch-adversarial-review | completeness-audit | final-handoff-decision]
- current_domain: [goal-and-users | triggers-and-primary-flow | boundaries-and-non-goals | failure-paths-exceptions-and-permissions | dependencies-constraints-and-upstream-downstream-impact | acceptance-and-completeness-gap-closure | none]
- next_action: [Smallest next discovery action to take]
- blocker_reason: [None | Why progress is blocked or why a domain was reopened]
- final_handoff_decision: [/sp.plan | /sp.clarify | /sp.deep-research | undecided]

## Allowed Artifact Writes

- [Artifacts this workflow pass may write, e.g. spec.md]

## Forbidden Actions

- [Actions this workflow pass must not take, e.g. edit source code]

## Authoritative Files

- [Files that are currently treated as the source of truth, e.g. spec.md]

## Next Command

- [`/sp.plan` | `/sp.clarify` | `/sp.deep-research` | other canonical next workflow token]
