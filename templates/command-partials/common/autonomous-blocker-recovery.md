## Autonomous Blocker Recovery

This contract applies to `sp-fast`, `sp-quick`, `sp-implement`, and `sp-debug`.
Blocker category does not define the repair boundary. Classify ownership from
the proven control boundary and available authority, not from the subsystem
name, the original plan, or the initial write scope.

Repository- or machine-local failures are agent-owned recovery work when the
Agent can repair them safely and within the user's authorization. This includes
launcher and child-process tracking, a test harness or fixture, browser and CLI
runners, dependency restoration and local caches, build or startup tooling,
configuration, a local service, generated tooling, repository scripts, and
project-local runtime state. A failure discovered during validation does not
become user-owned merely because its fix touches supporting code outside the
initial write scope.

When such a failure blocks delivery:

1. Preserve the parent workflow, active item/task, evidence, and failed gate.
2. Diagnose the owning failure mechanism from evidence. An unknown root cause
   starts or deepens diagnosis; it is not itself a terminal blocker.
3. Create or amend the smallest tracked recovery item/lane under the current
   runtime owner. Expand the owned scope before editing, including Work Board
   intent or lifecycle scope where those controls apply. Never use recovery to
   absorb unrelated improvements.
4. Establish the focused RED/reproduction or before-state, repair the root
   cause, verify the control plane, and resume the exact interrupted gate in the
   same invocation. Run evidence-driven diagnosis and tracked repair as an
   internal lane of the active workflow. Do not invoke another user-invoked
   workflow automatically; when a canonical runtime owner must act, use its
   declared CLI operation without impersonating or rewriting that workflow.
5. Do not repeat an unchanged failing command. Strengthen evidence,
   instrumentation, isolation, or the repair fingerprint before retrying.
   Retry count alone never converts agent-owned work into an external blocker.

Stop only when no safe authorized agent action remains and evidence proves a
real human or external boundary: unavailable credentials or permission that
the Agent cannot request, a protected external system, an unauthorized external
write, a human decision or review, required physical access, or confirmation
for a destructive or materially irreversible action. Use the shared Blocked
Exit Contract then. Complexity, unfamiliar technology, time spent, a changed
file count, or being outside the first execution packet is not such a boundary.
