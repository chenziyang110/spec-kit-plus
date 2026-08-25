# Autonomous blocker recovery

Read this reference for `spx-fast`, `spx-quick`, `spx-implement`, and
`spx-debug` whenever execution, validation, or recovery cannot immediately
continue. Blocker category does not define the repair boundary. Determine
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

Only a proven boundary with no safe authorized agent action may stop: credentials
or permission the Agent cannot obtain or request, a protected external system,
an unauthorized external write, a human decision or review, physical access,
or confirmation for a destructive/materially irreversible action. Then read
`references/blocker-resolution.md`. Complexity, unfamiliar technology, elapsed
effort, changed file count, or a path outside the first packet is not a human
boundary.
