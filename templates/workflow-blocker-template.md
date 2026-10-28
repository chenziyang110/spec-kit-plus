# Workflow Blocker

For every `sp-*` and `spx-*` invocation, apply the Recovery Decision before
choosing a blocked exit. Use the terminal view only after the workflow has
exhausted safe, authorized recovery and independent dependency-ready work.
Do not create a separate artifact merely to repeat information already owned by
workflow state or a task lifecycle record.
Project-controlled launcher, harness, dependency, build/startup, local-service,
or supporting-scope failures are not eligible for this terminal view merely
because validation discovered them or they were outside the initial packet.

## Recovery Decision (Agent-Only)

Invoking a workflow preauthorizes the necessary diagnosis, safe recovery,
verification, and continuation within its current goal, available permissions,
and allowed side effects. Do not ask for routine permission for an obvious,
reversible next step. Apply this procedure; do not copy it into the user report.

1. Preserve the parent workflow, item, failed gate, original error, and evidence.
   Inspect current inputs, live source, tool help/capabilities, and owner state
   before concluding that information or functionality is unavailable. An
   unknown root cause starts diagnosis; it does not justify escalation.
2. Respect read-only and stage boundaries. Read-only work may inspect alternative
   live evidence, but must not write files, restore dependencies, modify caches,
   or create workflow state. Planning repairs only its owned planning artifacts.
   Authorized modifying workflows may expand the smallest necessary supporting
   scope through the existing Work Board/lifecycle owner before editing. Never
   absorb unrelated improvements or overwrite unrelated user changes.
3. Treat local stop/halt/fail-closed instructions, including exit `10`, as a stop
   on the invalid operation, not on safe diagnosis or authorized recovery.
   Rebuild missing owned artifacts, repair invalid owned inputs, refresh stale
   evidence, restore permitted tooling, or redispatch through their declared
   owners. Never bypass a gate, hand-edit runtime state, change requirements or
   approvals, fabricate evidence, or invoke another user-invoked workflow
   automatically. A required new stage remains an explicit authorization
   boundary when no recovery operation is authorized in the current workflow.
4. Establish a focused reproduction or before-state, apply the smallest causal
   fix, and verify its result. Do not repeat an unchanged deterministic failure;
   improve evidence, instrumentation, isolation, or repair strategy first.
   Transient retries need bounded backoff and evidence that conditions may
   change; no indefinite polling. Retry count alone, complexity, unfamiliar
   technology, elapsed effort, or changed-file count does not transfer ownership.
5. Continue independent dependency-ready work; do not cross an unaccepted
   prerequisite. A blocked worker result returns to the leader for recovery,
   not directly to the user. Preserve required independent validation and keep
   it pending when unavailable; self-verification is not independent acceptance.
6. Resume the exact interrupted gate in the same invocation after repair, then
   continue the original workflow to its full completion criteria. Revalidate
   affected downstream evidence. Repair success, one passing lane, or a partial
   result is not completion. Never weaken acceptance criteria or skip mandatory
   checks. Use runtime-returned resolution/reopen actions with actual evidence;
   a stored blocked status is not by itself a terminal exit.
7. Exit incomplete only when no safe authorized recovery or independent work
   remains. Prove the remaining capability, authority, external-system, human
   decision/review, physical-access, or destructive-confirmation boundary.
   Keep the real owner, attempted actions and results, remaining scope, observable
   unblock criteria, and exact resume point. Set `human_action_required: true`
   only for a specific necessary human action, not simply for an unavailable
   tool, external outage, or failed attempt. Otherwise keep
   `human_action_required: false` and the human guide null; do not disguise a
   capability limit as a user task.

## Blocked

- Blocker ID: `<stable workflow-local id>`
- Workflow / stage: `<sp-* or spx-*>` / `<stage>`
- Category / owner: `<category>` / `<agent|user|maintainer|external-system>`
- What is blocked: `<one-sentence summary>`
- Why it is blocked: `<specific cause, not only "validation failed">`
- Evidence: `<sanitized command output, status, artifact path, or external result>`
- Automatic recovery attempted: `<action -> result; write none when none was safe>`
- Affected scope: `<what cannot continue and what remains safe>`
- Exact next action: `<smallest action that can change the state>`
- Unblock criteria: `<observable result>`
- Resume point: `<command or exact instruction>`

## Human Action Guide

Include this section only when `human_action_required: true`.

- Goal: `<what the human will accomplish>`
- Why a human is required: `<authority, credential, external UI, subjective
  decision, physical device, or protected environment the agent cannot own>`
- Before you start: `<required account, role, URL, artifact, branch, or local
  state>`
- Safety: `<what must not be pasted, changed, approved, or retried blindly>`

1. **<Step title>** — `<exact click path or command, with placeholders
   explained>`
   - Expected: `<visible success signal>`
   - If not: `<diagnostic or safe alternative>`
2. **Verify** — `<independent check that the blocker is actually removed>`
   - Expected: `<observable result>`
   - If not: `<what evidence to collect instead of guessing>`

Return `<specific status, sanitized output, URL/ID, screenshot, or decision>`.
Never return secrets, session cookies, private keys, or full access tokens.
Then resume with `<command or exact message>`.
