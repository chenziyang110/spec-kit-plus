# Autonomous blocker recovery

Read this reference for all `spx-*` workflows whenever intake, execution,
validation, or recovery cannot immediately continue, before deciding to stop.
Recover first while keeping the failed gate closed. Invoking a workflow authorizes necessary diagnosis, safe recovery, verification,
and continuation within the current goal, available permissions, and allowed
side effects. Do not ask for routine permission for an obvious reversible step.
Apply the Recovery Decision in `.specify/templates/workflow-blocker-template.md`;
a blocked gate is not itself a terminal user handoff.

Blocker category does not define the repair boundary. Determine
ownership from the proven control boundary and available authority, not the
subsystem label, the initial plan, or the initial write scope.

Treat repository- and machine-local control-plane faults as agent-owned when
they can be repaired safely within the user's authorization: launcher and
child-process tracking, a test harness or fixture, browser/CLI runners,
dependency restoration and caches, build or startup tooling, configuration, a
local service, generated tooling, repository scripts, and project-local runtime
state. Supporting code outside the initial write scope does not become
user-owned merely because validation exposed it.

Preserve read-only and stage boundaries: read-only workflows use alternative
live evidence without writes to files, dependencies, caches, or workflow state;
planning repairs only its owned artifacts. Supporting write-scope expansion is
available only to an authorized modifying workflow through its current owner.
A local stop, halt, or fail-closed instruction (including exit `10`) stops the
invalid operation, not safe diagnosis or authorized recovery. Do not cross a
failed gate, rewrite an upstream approval, or start an unrequested stage.

On a recoverable failure:

1. Preserve the parent workflow, current item/task, evidence, and failed gate.
2. Diagnose the owning mechanism. An unknown root cause deepens the diagnostic
   lane; it is not a terminal blocker.
3. Add the smallest recovery item or lane through the current runtime owner and
   expand the owned scope before editing, including Work Board or lifecycle
   scope when applicable. Exclude unrelated improvement.
4. Capture a focused RED/reproduction or before-state, repair the cause, verify
   the control plane, and resume the exact interrupted gate in the same
   invocation. Keep diagnosis and tracked repair inside the active skill. Do
   not invoke another user-invoked workflow automatically; when a canonical
   runtime owner must act, use its declared CLI operation without impersonating
   or rewriting that workflow.
5. Never retry an unchanged deterministic failure. Improve evidence,
   instrumentation, isolation, or the repair fingerprint first. Transient
   retries require bounded backoff and a reason to expect changed conditions;
   never poll indefinitely. Retry count alone never makes agent-owned work
   external.
6. Continue independent dependency-ready work. A worker's blocked result goes
   to the leader for diagnosis, repair, or authorized redispatch, not directly
   to the user. Keep required independent validation pending when unavailable;
   an authorized fallback is not fictitious independent acceptance.
7. After repair, resume the exact interrupted gate and continue the original
   workflow to its full completion criteria. Revalidate affected downstream
   evidence; repair success alone is not workflow completion.

Match recovery to current evidence:

- Missing inputs: locate and verify source artifacts, paths, tools, and documented
  prerequisites; restore reproducible inputs through their owner. Never invent
  requirements, approval, evidence, or accepted dependencies.
- CLI/schema/revision errors: inspect installed API/help and current owner state,
  correct the payload/binding, and use declared guarded recovery/resume actions.
  Never edit runtime storage or reset state to clear a gate. Reconcile interrupted
  processes and side effects before retrying.
- Delegation: discover native capabilities, repair packets, redispatch failed
  lanes, or serialize overlapping writes. Retain mandatory delegation and
  independent acceptance; only the owning workflow may permit a fallback.
- Validation: diagnose supported remaining defects after a failed autofix.
  Read-only/review workflows keep their source-write boundary and route product
  changes to their declared owner.
- Advisory cognition: use bounded live evidence when permitted if navigation is
  unavailable; required closeout still uses runtime-owned inspection/repair/replay.
  Missing navigation cannot prove completion.

Honor the user's verification budget: reuse unchanged valid evidence, run the
narrowest meaningful repair check and interrupted gate, and avoid full suites
or unrelated cleanup. Continue independent safe lanes while dependencies wait.
Provide concise progress updates instead of asking routine repair permission.

Only a proven boundary with no safe authorized agent action may stop: credentials
or permission the Agent cannot obtain or request, a protected external system,
an unauthorized external write, a human decision or review, physical access,
or confirmation for a destructive/materially irreversible action. Then read
`references/blocker-resolution.md`. Complexity, unfamiliar technology, elapsed
effort, changed file count, or a path outside the first packet is not a human
boundary. A proven unavailable capability or external outage with no remaining
safe path may require a resumable incomplete result. Keep its real owner and
`human_action_required: false` unless a specific human action is necessary.
Never weaken acceptance criteria, skip mandatory checks, fabricate evidence,
overwrite unrelated user changes, or label partial work complete.

An immutable upstream contract needing a new user decision or an unavailable
mandatory capability may require its declared handoff. Recovery grants no new stage authority,
source-write permission, or cross-workflow invocation. Blocked state is resumable work,
never successful completion.
