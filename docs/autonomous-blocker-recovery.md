# Autonomous blocker recovery

Every Classic `sp-*` and Advanced `spx-*` invocation owns the safe, authorized
work needed to overcome execution obstacles and complete its original goal.
Discovering an error is not a terminal user handoff. A blocked runtime gate may
remain recorded while the agent diagnoses and repairs its cause.

## Recovery and completion

The agent preserves the parent workflow, active item, failed gate, original
error, and evidence. It inspects live inputs and capabilities, identifies the
owning failure mechanism, makes the smallest permitted repair, verifies the
repair, and resumes the exact interrupted gate in the same invocation. It then
continues the original completion criteria and revalidates affected downstream
evidence. Fixing the obstacle alone is not completing the workflow.

Continue independent dependency-ready work while one lane recovers. A worker's
blocked result is input to the leader's recovery loop, not permission to assign
the repair to the user. Never cross an unaccepted prerequisite or substitute
self-verification for required independent acceptance.

An unknown root cause, first failure, supporting path outside the initial
packet, unfamiliar technology, complexity, elapsed effort, or retry count is
not sufficient reason to escalate. Deterministic retries need new diagnostic
evidence or a changed repair. Transient retries need bounded backoff and a
reason to expect changed conditions; the contract does not require endless
polling or blind retries.

## Boundaries that remain in force

Invocation authorizes necessary recovery within the current goal, available
permissions, and allowed side effects; it does not grant arbitrary new rights.
Read-only workflows remain read-only, including files, caches, dependencies,
and workflow state. Planning repairs only its owned artifacts. Authorized
modifying workflows may register narrowly expanded supporting repair scope
through the existing owner before editing.

A local stop, halt, or fail-closed instruction, including exit `10`, stops the
invalid operation, not safe investigation or authorized recovery. It never
permits crossing a failed gate, editing another owner's state, inventing
approval, changing the user's requirements, weakening acceptance criteria, or
starting another user-invoked workflow automatically. A genuinely unrequested
stage or protected side effect still needs the appropriate authorization.

A terminal incomplete result is allowed only when no safe authorized recovery
or independent work remains. Preserve the real owner, evidence, actions and
results, remaining scope, observable unblock criteria, and exact resume point.
Set `human_action_required` only for a specific necessary human action. An
external outage or unavailable capability is not automatically a user task.
Never request secrets or replace a concrete next action with “ask a human.”

## Delivery path and ownership

Classic's shared renderer injects
`templates/command-partials/common/blocker-resolution.md` into every command
that does not already include it. That contract requires the Recovery Decision
in the installed `.specify/templates/workflow-blocker-template.md` before a
blocked exit. The four execution-specific recovery lanes retain their more
detailed `autonomous-blocker-recovery.md` guidance; they are not the coverage
boundary.

Advanced's shared renderer injects the blocked-exit reference into every skill.
Its installed `references/blocker-resolution.md` requires
`references/autonomous-blocker-recovery.md` for every workflow before deciding
that failure is terminal. Both shared references are installed per skill and
participate in missing-file repair. The three Classic map companions continue
to use the unchanged Classic renderer.

No new state machine, blocker schema, runtime mutation command, profile fork,
or lifecycle owner is introduced. Existing revision-bound resolution,
reconciliation, and atomic reopen actions remain authoritative. The recovery
policies and terminal template already belong to the wheel's packaged assets.
Existing projects receive the new policy through normal workflow-asset
regeneration/update; missing-file repair alone is not an upgrade of existing
files. Preserve user-modified assets rather than editing generated copies by
hand. This change does not publish a release.

## Regression scenarios

These are behavioral acceptance scenarios for real agent evaluations. The
Python suites below verify prompt delivery, policy invariants, and installation;
they do not claim to prove a model's decisions or a passing product workflow.

| Scenario | Required continuation | Prohibited shortcut |
| --- | --- | --- |
| Missing permitted local dependency or broken test launcher | Diagnose and repair through the current owner; rerun the interrupted check and finish the original task | End with instructions for the user to run a repair the agent can perform |
| First failure or unknown cause | Obtain discriminating evidence and a focused reproduction | Label complexity or unfamiliarity an external blocker |
| Owned planning payload fails validation | Repair that planning payload through its artifact owner, then revalidate | Edit production source or rewrite approved upstream input |
| Read-only evidence path unavailable | Inspect alternative live evidence and report remaining uncertainty accurately | Install dependencies, mutate caches, or create workflow state |
| One worker/lane is blocked | Recover under the leader and continue independent ready lanes | Treat the worker's status as accepted or stop the whole task |
| Repair succeeds | Rerun the original failed gate and affected consumers; complete the original criteria | Report task completion after only the repair passes |
| Repeated deterministic or transient failure | Improve evidence/strategy; bound justified transient retries | Spin on unchanged inputs or convert retry count into user ownership |
| Missing capability or external outage | Exhaust permitted alternatives and preserve an incomplete resume point | Invent a human action when none can resolve it |
| Protected credentials, approval, or irreversible action | Request only the necessary authorized human action with a concrete guide | Ask for secrets, bypass authorization, or fabricate approval |
| Independent validator unavailable | Try supported dispatch/fallback and preserve the independent gate as pending | Present self-verification as independent acceptance |

Run the focused suites and the existing rendering/profile regressions:

```bash
python -m pytest tests/test_autonomous_blocker_recovery_contract.py \
  tests/test_global_autonomous_recovery_contract.py \
  tests/integrations/test_global_blocker_recovery.py
python -m pytest tests/test_spx_skill.py \
  tests/integrations/test_base.py \
  tests/integrations/test_unified_specify_runtime_rendering.py \
  tests/integrations/test_advanced_skill_repair.py
```

The global integration suite discovers actual catalogs, verifies installed
Classic and Advanced references on Codex/Claude plus Classic TOML on Gemini,
covers Bash/PowerShell rendering, tests missing-file repair and preservation of
user edits, and checks wheel inclusion. Keep local tests, cloud CI, real-agent
scenario evaluations, and release/distribution verification as distinct claims.
