## Autonomous Blocker Recovery

This contract applies to every `sp-*` workflow, including delegated lanes.
Before treating a workflow-local `stop`, `blocked`, or escalation instruction
as a terminal exit, attempt the safe recovery below. A failed gate remains
closed during recovery; it does not end the invocation by itself.
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

Choose the smallest recovery that fits the observed failure:

- Missing input: locate and validate existing source artifacts, paths, local
  tools, and documented prerequisites; restore reproducible inputs through their
  owner. Never invent requirements, approval, evidence, or accepted dependencies.
- CLI/schema/revision failure: inspect the installed API/help and current owner
  state, correct the payload or stale binding, then use its declared guarded
  recovery/resume operation. Never edit runtime storage or reset a workflow to
  clear a gate. Recover interrupted processes and side effects before retrying.
- Delegation failure: discover the actual native surface, repair the packet,
  redispatch a failed lane, or serialize overlapping writes. Preserve mandatory
  delegation and independent acceptance; use only a fallback the owner permits.
- Validation failure: diagnose and repair remaining supported defects rather
  than stopping because one autofix failed. Read-only/review workflows retain
  their source-write boundary and route product changes to their declared owner.
- Advisory cognition unavailable: continue with bounded live evidence where the
  workflow permits it. Required cognition closeout still uses runtime-owned
  inspection/repair/replay; unavailable navigation never proves completion.

Honor the user's verification budget. Reuse unchanged valid evidence and run
the narrowest meaningful repair check plus the interrupted gate; recovery does
not authorize a full test suite or unrelated cleanup. Continue independent safe
lanes while a dependent gate is closed. Give concise progress updates during
recovery instead of requesting routine permission to investigate or repair.

Stop only when no safe authorized agent action remains and evidence proves a
real human or external boundary: unavailable credentials or permission that
the Agent cannot request, a protected external system, an unauthorized external
write, a human decision or review, required physical access, or confirmation
for a destructive or materially irreversible action. An immutable upstream
contract requiring a new user decision or an unavailable mandatory capability
may also require its declared handoff; recovery grants no new stage authority,
source-write permission, or cross-workflow invocation. Use the shared Blocked
Exit Contract only after applicable recovery is exhausted, preserving attempted
actions and the exact remaining gate. A blocked state is resumable work, never
successful completion. Complexity, unfamiliar technology, time spent, a changed
file count, or being outside the first execution packet is not such a boundary.
