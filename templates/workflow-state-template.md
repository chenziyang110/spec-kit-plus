# Workflow State: [FEATURE NAME]

## Fixed Lifecycle State

- current_stage: [intent-analysis | intent-confirmation | question-batch | batch-adversarial-review | completeness-audit | final-handoff-decision]
- current_domain: [goal-and-users | triggers-and-primary-flow | boundaries-and-non-goals | failure-paths-exceptions-and-permissions | dependencies-constraints-and-upstream-downstream-impact | acceptance-and-completeness-gap-closure | none]
- next_action: [Smallest next discovery action to take]
- blocker_reason: [None | Why progress is blocked or why a domain was reopened]
- final_handoff_decision: [/sp.plan | /sp.clarify | /sp.deep-research | undecided]
