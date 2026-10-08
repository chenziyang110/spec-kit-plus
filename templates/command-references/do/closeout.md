# Do Closeout

Trigger: read before knowledge updates, final completion, source closeout, or a
blocked stop.

Preserved Contract: execution outcome and knowledge outcome are separate. A
successful native command does not by itself finish DO, and a useful proposal
does not turn a failed operation into a success.

Use fresh `do validate <id>` and the runtime-returned `do finish` contract.
`ready_to_finish` means the execution may be finalized; it is not already a
terminal receipt. Re-read `do show <id>` and require `data.terminal=true` before
claiming this invocation complete. If execution passed but method persistence
is still pending, report that split and resume only the missing knowledge step;
do not rerun an already successful external operation.

For a verified method update, preserve this order:

1. Finish validated execution with
   `do finish <id> --input-json '{"expected_revision":<current>,"knowledge_status":"pending"}'`.
   The runtime sets execution to passed only after the frozen checks and source
   closeout gates pass; the session remains resumable for knowledge persistence.
   Capture a policy-eligible Learning signal now, before method persistence,
   through `learning capture-auto --command sp-do --session-id <id>` or manual
   `learning capture --command sp-do --session-id <id>`. Routine passing output
   does not justify a lesson; a real capture registers its exact metadata scope.
2. Call `playbook update` with the exact verified definition, matching completed
   `session_id`, and current `base_digest` when updating an existing method. An
   unchanged method still records usage and returns a receipt without creating
   another revision. Retain the returned `data.knowledge_receipt`.
3. Read `do show <id>` again: the method write may have advanced the session
   revision while expanding its Work metadata scope. Finish with that current
   `expected_revision`, `knowledge_status="saved"`, and the complete returned
   receipt as `knowledge`. Do not synthesize its path, hash, method ID, or revision.

Use `not_applicable` with a concrete reason when no reusable method or usage
should be retained. Capture a significant sanitized Learning signal through its runtime
API when its policy permits; otherwise record the honest no-learning outcome.

## Source Mutation

If DO created or changed retained project source, scripts, tests, or configuration,
read [Source mutation](source-mutation.md) and apply its complete shared
`sp-do` closeout before `do finish`. It binds the existing session directory,
exact owned source paths, current checks, and runtime receipt. Failed, blocked,
or interrupted execution does not erase an owned source delta or its pending
closeout obligation.

When the operation only produced declared outputs or changed playbook/session
metadata, record the runtime's explicit `no_source_mutation` / not-applicable
disposition. Do not fabricate graph facts or call an invented cognition no-op
command. Cognition at intake is advisory; source-mutation closeout is a separate
completion gate and cannot be replaced with a stale map-status assertion.

## Blocked Exit and User Result

Keep agent-owned diagnosis, local repair, retries, and state recovery inside the
same invocation. Stop only at a real authorization, credential/access, external
system, destructive decision, or unresolved user-owned boundary. Report the
session ID, failed step/check, exact sanitized cause, attempted recovery,
preserved outputs and source edits, next action, observable unblock condition,
and exact resume command. Never transfer routine runtime-state repair to the user.

For such a genuine blocker, use `do finish` with the current `expected_revision`
and the schema's `blocker`: category, owner `human` or `external`, cause,
attempted recovery, actual scoped evidence refs, next action, unblock criteria,
and resume point. Keep knowledge pending. A runtime-accepted blocker holds Work
ownership and returns `can_stop=true` with `terminal=false`; this permits an
honest blocked exit, never a completion claim. Agent-owned failures remain in
active recovery. Resume after resolution through `do resume` with fresh recovery
evidence, inspected effects, and prior processes stopped. Resolving an external
blocker does not silently retry a separately interrupted attempt.

The final response must state the actual operation outcome, what was verified,
requested output locations, whether a method was reused/updated/proposed, and
any remaining gap. Explain a measured efficiency gain only if comparable
observations support it; do not turn a single faster run into a broad claim.
Project-local methods are not automatically committed or shared across machines.
