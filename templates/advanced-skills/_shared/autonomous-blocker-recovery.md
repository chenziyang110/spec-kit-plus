# Autonomous blocker recovery

Read this reference for every `spx-*` workflow, including delegated lanes,
before interpreting a local `stop`, `blocked`, or escalation as a terminal exit.
Recover first while keeping the failed gate closed. Blocker category does not
define the repair boundary. Determine
ownership from the proven control boundary and available authority, not the
subsystem label, the initial plan, or the initial write scope.

Treat repository- and machine-local control-plane faults as agent-owned when
they can be repaired safely within the user's authorization: launcher and
child-process tracking, a test harness or fixture, browser/CLI runners,
dependency restoration and caches, build or startup tooling, configuration, a
local service, generated tooling, repository scripts, and project-local runtime
state. Supporting code outside the initial write scope does not become
user-owned merely because validation exposed it.

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
5. Never retry an unchanged failure. Improve evidence, instrumentation,
   isolation, or the repair fingerprint first. Retry count alone never makes
   agent-owned work external.

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
or confirmation for a destructive/materially irreversible action. An immutable
upstream contract needing a new user decision or an unavailable mandatory
capability may require its declared handoff. Recovery grants no new stage
authority, source-write permission, or cross-workflow invocation. Only after
applicable recovery is exhausted, read `references/blocker-resolution.md` and
preserve attempts and the exact remaining gate. Blocked state is resumable work,
never successful completion. Complexity, unfamiliar technology, elapsed
effort, changed file count, or a path outside the first packet is not a human
boundary.
