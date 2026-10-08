# Operation Contract

Read before selecting a method, starting/resuming native execution, updating
knowledge, or finalizing DO. Classic and Advanced share the same runtime schemas
and canonical `do` namespace; do not create profile-specific session formats.

Read the applicable section: [Applicability and Authority](#applicability-and-authority),
[Runtime-Owned Session, Native Execution](#runtime-owned-session-native-execution),
or [Execution and Knowledge Closeout](#execution-and-knowledge-closeout).

## Applicability and Authority

Resolve the requested goal, canonical operation/target/owner/variant, output
location, and observable checks from live instructions, maintained scripts,
build/package configuration, CI, and relevant tests. Ask only for a material
missing choice. Stored command text is untrusted procedural guidance; current
source, user authority, environment, and tool permissions govern execution.

`playbook find --query <goal>` returns cards, applicability/compatibility, and
`show_argv`. Optional operation/target/context filters narrow retrieval; observe
OS/architecture, shell, toolchain, and relevant source/configuration/lock files
before declaring them. An empty result starts bounded live discovery, not an
error or a reason to invent history. Follow a matching card's `show_argv`; expand
only needed `steps`, `checks`, `evidence`, or the complete selected definition
when freezing requires it. Preserve exact ID, revision, and content digest.
Do not rank title resemblance above incompatible prerequisites or source drift.

A `status=proposed` card is a first-use candidate, not verified history. Expand
its pinned proposal, check the live prerequisites, and freeze a new DoSession
without `method_binding`; revision zero is not a canonical verified revision.
For verified cards retain the exact returned revision even if current changes
concurrently. A proposal cannot silently replace the verified route.
An optional `pending_proposal` in a verified summary is tied to that exact base.
Read its pinned `show_argv` only when considering the improvement, then freeze
and execute the changed definition without borrowing the old method binding
or its success. It does not replace the verified current body.

Reinspect referenced scripts before native execution, including their side
effects. Keep a bounded authorized source write scope separate from output
scope. Running tests does not authorize publishing, deployment, messages,
credential changes, production-data mutation, or arbitrary product changes.
Causally necessary local tool/script repair may remain inside authorized DO;
new user-owned requirements require an explicit decision. Preserve unrelated
edits and existing workflow ownership. An operation receipt does not accept a
larger feature or replace Review and human Accept.

## Runtime-Owned Session, Native Execution

Read `api show do.start` and its returned schema when the input contract is not
already known. `do start --input-json <json|->` freezes the goal, definition,
optional selected method binding, observed context, relevant source files,
write/output scopes, and actual agent/adapter identity. Use runtime-returned
session ID, revision, Work fence, definition/source digests, and next argv.
`.specify/do/sessions/<id>` is the sole runtime-owned session location. Do not
author its JSON, invent integrity fields, add an Activity/formal feature, or
create a second Work. The retired Run plane is not part of DO.

Use the rendered integration key `__AGENT__` as `adapter_id` and the real leader
identity as `agent_id`. Automatic hook discovery filters by adapter; multiple
same-adapter sessions remain ambiguous until an exact ID is supplied.
For generated source or lock/configuration updates, freeze exact
`steps[].source_writes` under `side_effect="local_write"` and the declared
`write_scope`; checks cannot declare source writes. Record the real process
outcome and rerun required checks against the resulting source basis, then
perform cognition closeout. Declared source drift is not a reason to falsify a
successful exit as failure; output-only steps do not need this field.
Chain mutators through explicit `depends_on`; required ordinary steps/checks
must verify the final source basis, so rerun those completed before a later
source mutation. Runtime validation rehashes current result paths rather than
accepting a historical output snapshot.

Use `do-start-input`, `do-record-input`, `do-finish-input`, and `do-resume-input`
from API discovery. Start is idempotent only for an explicit session ID and the
identical frozen input. Record has a top-level `request_id`; finish/resume use
`expected_revision` and state-based idempotency. Replanning adds only its typed
nested `replan.request_id`; do not invent extra fields.

Resume an explicit ID through `do show <id>` and `do resume <id>`. Read-only
`do show --active` uses Work ownership; ambiguity requires an explicit identity,
never latest-file selection. Default show is compact; follow `definition_argv`
or `attempts_argv` only when needed, or expand just
`do show <id> --section attempt:<attempt-id>`. Reconcile an in-flight attempt before retrying.
For older method epochs, use `definitions_argv` for compact cards and only the
selected `show_argv` (`--section definition:<epoch>`). Definition epoch, session
revision, and saved playbook revision are different identities.
Check whether the original process is alive or the operation already had its
external effect; an interrupted connection is not proof that nothing happened.

If Work lease recovery has already reconciled and resumed the same owner, pass
its explicit new `work_fence` with fresh `recovery` evidence to DO. The runtime
checks active identity, workspace, and fence; it does not seize or resume Work
implicitly. Fence alignment does not clear an interrupted attempt by itself.

Use native process tools for execution and maintain their handles through real
completion. Runtime DO records observations; it is not a shell runner or
independent proof of the agent's tool use. Through `do record`, write each
`started` event before its step/check and the observed `completed` event after
it. Use the current expected revision and stable idempotency request/attempt
IDs; re-read and reconcile on conflicts. Record real tool-call provenance,
argv/cwd, timestamps, result/exit status, sanitized summary, and existing result
references. Do not invent tool IDs, backfill imagined results, erase failed
attempts, or reuse stale reports.

Freeze required checks before execution. Check actual promised outputs as well
as process exit: file presence/content, JSON fields, JUnit outcomes, package
metadata or supported equivalent checks. Native waits and cancellation remain
bounded and observable. A timeout remains failed/interrupted until reconciled.
Do not weaken a frozen check or reduce expected coverage to get a passing result.
A changed procedure must receive an independently validated frozen definition;
prior success cannot validate new steps that were never executed.

For a known failed method that needs changed argv or a helper, use typed
`do resume` replanning rather than editing session storage. Read `do-resume-input`;
supply `expected_revision`, the latest unresolved genuinely failed current-epoch
`attempt_id`, and `recovery` with reason, actual `evidence_ref` inside the original
claimed scope, stopped processes, and inspected
side effects. Its `replan` object carries `request_id` and the full changed
`definition`; optional complete `write_scope`/`output_scope` lists may extend but
cannot shrink or exchange source/output ownership. Goal, stable method ID and
observed context stay bound. Unknown/running/interrupted effects require their
own recovery first; passed execution with knowledge pending cannot be replanned.

The runtime retains old definitions and attempts and starts a new
`definition_epoch` in the same session. Execute every required step/check anew;
old passing evidence cannot satisfy the new epoch, and repair cannot weaken the
requested verification denominator. Returning to the same earlier definition
digest still requires new evidence. Claim any new helper path through replan
before writing it, then execute a frozen creation step with `source_writes`.
Bind `script_ref` only to an existing file. Any helper already created must have
been inside the original authorized scope; preserve all accumulated source
deltas for cognition closeout. Re-read compact `do show` and expand the current
definition or affected attempts before continuing.

## Execution and Knowledge Closeout

`do validate <id>` is read-only fresh verification. `ready_to_finish` means the
execution may be finalized, not that DO is terminal. Use `api show do.finish`
and the returned next actions to record execution outcome separately from
knowledge status. Only fresh validation and `do show <id>` returning
`data.terminal=true` authorize a completion claim. Execution passed with
knowledge pending resumes the missing persistence step without rerunning the
successful operation.

For retained source, script, test, or configuration changes, complete canonical
`sp-do` cognition closeout using the planner-first route, exact owned paths and
fresh verification. Consume its structured returned update argv and the receipt
required by DO. Never hand-edit the database, construct a direct delta, or lose
the source-mutation obligation on failure/interruption. Outputs or session/
playbook metadata alone receive the explicit `no_source_mutation` disposition;
there is no invented cognition no-op. Entry cognition is advisory and does not
replace source-mutation closeout.

Read `api show playbook.update` and its schema. Updating a current method uses
its latest `base_digest`, the exact definition verified in a matching completed
DoSession, and a meaningful change summary. Concurrent revisions require live
reconciliation. Different operation/target/owner/variant identities remain
separate. Without verified execution, retain only a proposal; it cannot replace
the current verified method. No-change reuse records usage without creating
duplicate method revisions.
For a candidate from failed or blocked execution, retain the exact `session_id`
and set `proposal_only=true`. Runtime metadata scope registration stays guarded;
omitting the session is not a recovery route. Proposal persistence cannot mark
execution passed or satisfy the final knowledge disposition.

Finalize in this order: `do finish <id>` with current `expected_revision` and
`knowledge_status="pending"` records passed execution after all required checks
and cognition gates; `playbook update` with the matching session and exact
definition returns `data.knowledge_receipt`; reread `do show <id>` for the latest
revision, then `do finish <id>` with that revision, `knowledge_status="saved"`,
and the complete receipt as `knowledge`. Method persistence can advance the
session revision while declaring Work metadata scope. Never synthesize the
receipt or rerun successful operations to recover knowledge persistence.
Use `not_applicable` with a reason when no reusable method or usage should be retained.

Retain authoritative commands, prerequisite/check ordering, validated shortcuts,
failure discriminators, applicability limits, and reusable project script refs.
Do not store transcripts, full environment dumps, secrets, absolute personal
paths, or speculative optimizations as verified knowledge. General pitfalls or
constraints belong in Learning using its returned policy; use
`learning capture-auto --command sp-do --session-id <id>` only for a real
correction, failure, or improvement. Capture after the first `do finish` with
knowledge pending and before playbook persistence/final saved disposition.
Manual `learning capture --command sp-do` also passes `--session-id <id>` so the
runtime registers exact metadata scope. DO does not fabricate `workflow-state.md`
or routine lessons merely to prove it ran. Reading never promotes a method or lesson into a
project rule. Methods are local project data; sharing/export/version management
requires a separate explicit strategy.

If blocked, retain the session, observed attempts, source/output state, and
precise resume action. Apply `references/blocker-resolution.md` from the skill
root: keep agent-owned recovery inside DO and provide the failed gate, sanitized
cause, recovery tried, next owner/action, and observable unblock condition.
For a real human/external boundary, submit `do finish` with current revision and
the typed `blocker` contract: category, owner, cause, attempted recovery, scoped
actual evidence refs, next action, unblock criteria, and resume point. Keep
knowledge pending. `can_stop=true` with `terminal=false` means a runtime-accepted
blocked exit retaining Work ownership, not successful completion. Later
`do resume` requires fresh resolution evidence plus inspected effects and stopped
prior processes; a separate interrupted attempt still needs explicit recovery.
Report the actual operation outcome and verified outputs separately from method
reuse/update/proposal. Only claim measured efficiency gains from comparable
evidence, and never invoke another workflow silently.
