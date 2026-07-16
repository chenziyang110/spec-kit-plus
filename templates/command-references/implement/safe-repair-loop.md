Trigger: when validation fails, review rejects work, blockers appear, or task-layer defects are found.

Purpose: preserve safe repair ownership, blocker routing, tracker updates, and debug escalation behavior.

Preserved Contract: repair stays evidence-bound and routes unresolved defects to debug instead of speculative implementation.

## Actionable Blocker Resolution
- blocker: [task id or validation gate]
  classification: technical | external | human-action | verification_policy | project_cognition_readiness | baseline_timeout
  owner: agent | user | maintainer | external-system
  evidence: [artifact path, command output summary, or missing artifact]
  exact_next_action: [specific command, focused investigation, rerun, approval request, or upstream workflow]
  approval_question: [exact yes/no approval question when owner is user or maintainer, otherwise none]
  unblock_criteria: [observable condition that changes this from blocked to complete]
  implementation_can_continue: yes | no
  completion_impact: mandatory_for_completion | optional_cleanup | external_baseline_maintenance | follow_up_risk

## Blockers
- task: [task id]
  type: technical | external | human-action
  evidence: [short command output or observed failure]
  recovery_action: [smallest safe next recovery step]

## Open Gaps
- type: execution_gap | research_gap | plan_gap | spec_gap
  summary: [what is still not true]
  source: [task id, validation check, or user-visible outcome]
  next_action: [specific next step]

## Protected CI checkpoint

When a commit is technically required to obtain protected-CI evidence that is
`mandatory_for_completion`, keep the task unchecked and its task lifecycle
blocked with the Actionable Blocker Resolution fields above. Validate the
non-final commit with `specify hook validate-commit --commit-message <message>
--feature-dir <feature-dir> --commit-intent external-evidence-checkpoint`.
On Claude or Gemini native hooks, carry the explicit intent on the actual
commit with `git -c specify.commitIntent=external-evidence-checkpoint commit -m
"<message>"`; the hook binds it to the active feature and repeats the shared
validation.
Passing that gate permits only the local checkpoint: it does not mark the task
or tracker `resolved`, authorize a push/CI trigger, or weaken the ordinary final
commit and implementation closeout gates.
