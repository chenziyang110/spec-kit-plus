# Workflow State: [FEATURE NAME]

## Current Command

- active_command: [sp-specify | sp-plan | sp-tasks | sp-implement | sp-debug | sp-analyze | sp-deep-research | sp-clarify | sp-constitution | sp-prd | sp-prd-scan | sp-prd-build]
- status: [active | completed | blocked]

## Phase Mode

- phase_mode: [planning-only | design-only | task-generation-only | execution-only | analysis-only | research-only]
- summary: [Short current-state summary for resume and hook context]

## Fixed Lifecycle State

- current_stage: [facts-lock | route-lock | intent-lock | complexity-lock | intent-analysis | intent-confirmation | question-batch | batch-adversarial-review | completeness-audit | final-handoff-decision]
- current_domain: [goal-and-users | triggers-and-primary-flow | boundaries-and-non-goals | failure-paths-exceptions-and-permissions | dependencies-constraints-and-upstream-downstream-impact | acceptance-and-completeness-gap-closure | none]
- next_action: [Smallest next discovery action to take]
- blocker_reason: [None | Why progress is blocked or why a domain was reopened]
- final_handoff_decision: [/sp.plan | /sp.clarify | /sp.deep-research | undecided]

## Brainstorming Locks

- facts_lock: [pending | active | closed]
- route_lock: [pending | active | closed]
- intent_lock: [pending | active | closed]
- complexity_lock: [pending | active | closed]

## Unknown Handling

- hard_unknown_count: [0]
- soft_unknown_count: [0]
- next_unknown_to_resolve: [field or none]

## Reopen Contract

- reopen_source: [none | specify | plan | tasks | implement]
- reopen_target: [none | brainstorming | specify | plan | tasks]
- reopen_reason: [why a prior truth layer must be reopened]

## Handoff Files

- handoff_to_specify: [path or none]
- handoff_to_plan: [path or none]
- handoff_to_tasks: [path or none]
- handoff_to_implement: [path or none]

## Allowed Artifact Writes

- [Artifacts this workflow pass may write, e.g. spec.md]

## Forbidden Actions

- [Actions this workflow pass must not take, e.g. edit source code]

## Authoritative Files

- [Files that are currently treated as the source of truth, e.g. spec.md]

## Next Command

- [`/sp.plan` | `/sp.clarify` | `/sp.deep-research` | other canonical next workflow token]
