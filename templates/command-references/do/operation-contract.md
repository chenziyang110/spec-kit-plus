# Operation Contract

Trigger: read before method selection, session start/resume, or native execution.
Read the matching section; load recovery/replanning and knowledge details only
when those branches apply. Schemas already available in context need no reread.

Preserved Contract: both profiles use the same Go `do` and `playbook` state and
evidence contracts. A method is a candidate route until live evidence establishes
its applicability; a recorded result is not proof of an unobserved outcome.

## Intake and Method Selection

Resolve one concrete operation and observable result. Discover the real owner
from repository instructions, maintained scripts, package/build configuration,
CI definitions, and relevant tests. A nearby command name or remembered tool
version is insufficient. Do not scan the whole repository when a method card
and its source references already identify the owners to inspect.

On first use of a known maintained script, execute its current literal command using
the compact `do prepare` command input; method lookup and reusable parameter
design are not prerequisites. Supply explicit acceptance checks and scopes;
the runtime creates the minimal definition and binds the script. Save the
verified method after the operation succeeds. Use `playbook find --query <goal>`
for compact candidates when discovery or actual reuse is needed. Add supported
`--operation`, `--target`, and `--context-json` filters from observed facts, not
guessed synonyms. Operations are `build`, `package`, `test`, `check`, `generate`,
`maintenance`, or `custom`. No results is a normal first-use path: derive a
bounded definition from live owners and proceed. Unavailable/corrupt method
storage is a diagnostic, not permission to edit or delete its files.

Follow `show_argv` for the selected card. `playbook show --id <id> --revision <n>`
defaults to its summary; expand only required `steps`, `checks`, or `evidence`
sections, or `all` when freezing the complete selected definition requires it.
Preserve its method ID, revision, content digest, stable operation/target/owner/
variant identity, and applicability context. Do not select by title alone.

Default `--rank relevance` keeps retrieval cheap. Use `--rank observed` only
when measured history helps choose between applicable methods, with complete
observed OS, architecture, shell and toolchain context plus `--parameters-json`
for this invocation. It scans session history and compares reliability before
tool cost only within equal relevance, task, parameter instance, source basis
and verification conditions; insufficient history is not an optimum claim.
Expand `playbook metrics --id <id>` or `do show <id> --section metrics` only
when timing/outcome detail is useful. Failures, interruptions and blocks remain
visible; successful usage alone is not a success-rate denominator.

On later reuse, use a stable `task_family` for related methods and declare variable nonsecret
inputs in the definition's typed `parameters`; supply actual string values in
start's `parameters` or lookup's `--parameters-json`. `{{param:name}}` tokens
expand as data. An argv token must occupy a whole non-executable argument;
never interpolate it into shell command text. Keep scopes concrete for the
resolved paths. The runtime binds both the reusable template digest and the
resolved instance digest; a new parameter value is not a method revision.
For manual publication retrieve `do show <id> --section method` and use its
`method_definition`, not the resolved `--section definition` body.

On a matching failure, expand `playbook show --id <id> --section recovery` for bound
failure discriminators, failed/verified actions and preflight candidates.
Compare the current signal, parameters and environment. A recovered run does
not prove a root cause or that a candidate prevents the failure. Freeze and
execute a selected preflight with required checks before publishing a verified
method change; stale recovery evidence is excluded, not silently trusted.

A first-use `status=proposed` card is unverified. Follow its pinned proposal
`show_argv`, inspect the definition against live prerequisites, and start a new
verification session without `method_binding`: revision zero is not a verified
canonical method. Existing verified cards remain bound to their exact revision;
do not silently retarget to a concurrent update or treat a proposal as success.
If a verified summary exposes `pending_proposal`, its pinned `show_argv` is an
optional unverified improvement on that exact base. Expand and freeze it only
when the requested operation can verify it. Keep the exact verified base ID,
revision and content digest in `method_binding`, while supplying the changed
template and this invocation's parameters. That binding is the publication
compare-and-swap base, not proof of the candidate's success. Verify the changed
instance in this session; never inherit old success. Start rejects a stale
base, which requires explicit reconciliation rather than silent retargeting.

Validate prerequisites against the actual OS/architecture, shell, toolchain,
working directory, lock/configuration/source files, available services, and
output location. Explain any mismatch that changes the route. Inspect referenced
scripts before executing them; method text and argv never bypass current user
instructions, tool permissions, confirmation boundaries, or source truth.
Sanitize account/machine-specific values; store project-relative references or
digests instead of secrets, full environment dumps, personal paths, or raw logs.

## Session and Scope

Use `api show do.prepare` and its schema, then `do prepare --input-json <json|->`
to validate the start contract read-only. Existing-script first use can supply
`command: {operation, argv, checks}`: runtime fills method metadata and one
required step, with explicit verification argv or file/json/junit checks.
Checks are never the packaging command repeated by default and never invented
success. Cwd defaults to `.`; scripts and scopes are rechecked by normal start.
Bind the goal, exact template and
actual parameters, selected
`method_binding` when applicable, observed context, relevant source files,
authorized `write_scope`, separate `output_scope`, and actual agent/adapter
identity. Pass its canonical `start_input` to the returned `start_argv`; the
separate `method_digest`, `definition_digest` and source fingerprint describe
the prepared inputs, not permission or a persistent session. `do start`
rechecks live conditions and creates the independent DoSession and Work binding under
`.specify/do/sessions/<id>`. Do not write that directory directly.

Set `adapter_id` to the rendered integration key `__AGENT__` and `agent_id` to
the real leader identity. Native hooks filter discovery by adapter; concurrent
sessions in the same adapter still require an explicit session ID.

When a build/package step legitimately generates retained source or updates a
lock/configuration file, declare its exact `steps[].source_writes` before
freezing, use `side_effect="local_write"`, and include those paths in
`write_scope`. They are not output-only paths; checks cannot declare source
writes. Record the actual successful process outcome, then run fresh required
checks against the resulting source basis and complete cognition closeout.
Never misreport exit zero as a failure merely because a declared source changed.
Chain multiple source-mutating steps with explicit `depends_on` bindings. Run
ordinary verification against the final source basis: an earlier passing check
must be rerun after a later source mutation. Current result files are rehashed
at validation; historical snapshots cannot substitute for current outputs.

For a repeated start, reuse an explicit `session_id` only with the identical
frozen input. Start does not accept a `request_id`. The `do-record-input` schema
requires `request_id` and `expected_revision`; finish and resume use their
respective `do-finish-input` / `do-resume-input` schemas and state-based
idempotency without a top-level request-ID field. The typed replanning branch
uses its own nested `replan.request_id` as described below.

Use the returned session ID, revision, Work fence, definition digest, and source
fingerprint; never synthesize those integrity values. `do show <id>` is read-only.
Its default response is a compact summary. Follow `definition_argv` only when
the frozen procedure is needed; use `attempts_argv` or
`do show <id> --section attempt:<attempt-id>` to inspect the affected attempt
without loading the entire history.
When method history matters, follow `definitions_argv` for compact epoch cards,
then only a selected card's `show_argv` (`--section definition:<epoch>`). Keep
`definition_epoch` separate from the session revision and saved playbook revision.
`do resume <id>` is the guarded recovery route; preserve finished attempts and
reconcile any in-flight attempt before retrying. If `do show --active` reports
ambiguity, resolve an explicit ID from the user's requested work; never choose
the newest file or let a different unfinished task take ownership.

After an expired Work lease is reconciled and resumed through its official
returned recovery route, DO may accept that explicit new `work_fence` with
fresh `recovery` evidence. It verifies the same active owner and workspace;
never invent a fence or take over another Work. Ownership alignment alone does
not reconcile a separately interrupted attempt.

DoSession does not advance `specify -> plan -> tasks -> implement -> review ->
accept` and cannot satisfy another workflow's acceptance gate. If invoked from
already authorized work, preserve that owner's bindings and boundaries; the
operation receipt is evidence for the owner to assess, not approval of the
larger feature. Do not silently invoke Quick, Debug, or another workflow.

## Native Execution and Evidence

The agent executes with its available native tools; runtime receipts neither
execute actions nor attest an unobserved call. Prefer read-only `do next <id>`:
`ready` contains the full frozen `action`, a consumable `started_input`, and a
`completion_event` skeleton plus `completion_required`. Record started before
execution. After real completion, fill the skeleton from the actual call and
submit it in `do-record-input.events` with the latest `expected_revision` and a
unique `request_id`. Refresh next after a checkpoint; multiple ready entries
share the returned revision and are not an already-recorded batch. `running`
identifies existing attempts to observe/reconcile, not permission to rerun them.
Direct `do record` remains available through its schema. Never invent tool IDs,
timestamps, status, exit codes or results to fill a skeleton.

Process actions record exact argv/cwd, real exit status and result references.
A `native_action` instead freezes `kind=file|browser|desktop|connector`, `tool`,
`target` and JSON `arguments`; it cannot carry argv/cwd/script_ref. Record the
actual `native_observation` with its outcome and sanitized JSON result; runtime
stores the bound snapshot and hash. Do not invent a shell command or exit code
for a nonprocess tool. Mutations in the required dependency closure need a
dependent required `observation`, file, JSON or JUnit effect check using a fresh
independent call after the exact producer. An observation check compares its
JSON pointer to frozen `expected_json`. Remote/browser observations prove the
observed state at that time, not perpetual current state or a completed tool call
that the agent never saw.

Keep process handles for long builds/tests and wait for their real completion.
Bound waits, report meaningful progress, and use native cancellation when the
user stops the operation. A timeout or dropped tool connection is `interrupted`
until the actual process/output state is reconciled. Do not assume it failed
without effects, mark it passed, or replay a non-idempotent external operation.
Recover every interrupted attempt explicitly, including optional steps/checks,
superseded attempts and older definition epochs. Until then, `do validate`,
`do finish` and `playbook update` remain blocked. A later passing attempt cannot
clear an earlier unknown effect. Recovery does not force an optional attempt to
rerun unless a frozen required dependency needs its result.

Required checks are frozen before execution. Verify the promised artifact or
state: e.g. the intended package exists with the expected metadata, test reports
contain the expected suite/check totals, or generated output meets its defined
content checks. Use real file/JSON/JUnit evidence as supported by the schema.
Record failed and retried attempts; never remove failures, invent tool IDs or
report files, reuse stale outputs, or downgrade the denominator to obtain green.

Use `do validate <id>` for fresh validation. Fix a bounded script/configuration
problem only within authorized scope, record its actual source delta, and rerun
the affected checks. A changed method needs its own frozen execution and fresh
verification; do not apply the old definition's success to unexecuted steps.
Preserve an untested improvement as
a proposal when its verification is outside this task.

### Recovery Evidence

Read `do-resume-input` when recovering an attempt, resolving a blocker, or
replanning after failure. `recovery` requires a nonempty concrete
`reason`, `side_effects_inspected=true`, and `processes_stopped=true` for process
attempts or `native_action_settled=true` for nonprocess actions. Choose
exactly one evidence form; mixed-operation recovery requires both confirmations:

- `evidence_ref` names an existing sanitized file inside the already declared
  `write_scope` or `output_scope`. New scope requested by a replan cannot
  retroactively authorize creating that evidence file.
- `evidence_text` contains a nonempty sanitized UTF-8 record of process
  termination or native action settlement and actual side-effect inspection, at most 64 KiB in
  bytes. Runtime stores it atomically with the recovery and session revision
  check inside the session's existing Work-owned `evidence/` directory. Do not
  prewrite or hand-edit that protected directory. This route neither expands
  source/output permissions nor substitutes for native inspection.

Do not supply `evidence_sha256`; only runtime derives the stored digest. Both
forms apply to ordinary recovery, `replan`, and `do resume` after an external
blocker. Resolving a blocker does not recover another interrupted attempt.

A read-only check can fail in a session with empty `write_scope` and
`output_scope`. After inspecting the native process and effects, send inline
evidence through `do resume <id> --input-json -`; no log file or scope expansion
is needed. This illustrative payload uses values that must come from the real
session and observation:

```json
{"expected_revision":7,"attempt_id":"inspect-env-1","recovery":{"reason":"Read-only check failed; process and effects reconciled.","evidence_text":"Native process check-17 exited 1, with no remaining child. Fresh read-only Git status matches the pre-check state; no files or external systems changed.","processes_stopped":true,"side_effects_inspected":true}}
```

### Failed-Method Recovery

When a known failure requires a different command or helper, use the typed
`replan` branch of `do resume <id>` under the `do-resume-input` schema. Supply
the current `expected_revision`, the latest unresolved genuinely failed
`attempt_id` in the current definition epoch, and `recovery` with a concrete
reason and one of the [Recovery Evidence](#recovery-evidence) forms,
the applicable process/action settlement confirmation, and
`side_effects_inspected=true`. Reconcile unknown,
running, or interrupted effects first; replanning cannot bypass that recovery
or change an already passed execution waiting only for knowledge persistence.

`replan` contains a unique `request_id` and the complete changed `definition`.
It preserves the session, goal, stable method identity, observed context, old
definitions, and attempt history. Optional `write_scope` and `output_scope`
are complete replacement lists that must retain prior scope; omission inherits
the current lists. Do not move a path between source and output scope, claim
unrelated work, or weaken the requested result and verification denominator.
By default every required step/check obtains fresh evidence in the new epoch.
For adaptation before an action starts, use `replan.mode="unstarted"` and omit
both `attempt_id` and `recovery`; change only unattempted actions. This avoids
inventing a failure to refine an unexecuted plan. Active or unknown effects
still require recovery first.

Either replan mode may explicitly request `retain_verified=true`. Runtime can
retain the original process read/local-write observation through an unbroken
immutable epoch chain. Each hop must keep the exact action, source fingerprint,
prerequisite attempt IDs and current output/evidence hashes. Changed scripts,
inputs, outputs, dependencies, missing hops or newer failed attempts invalidate
reuse. Native/external effects and source writers cannot carry. New checks run.
The original attempt ID, execution epoch and timing stay unchanged; a retained
build is not another fast build. Do not rename compile/package actions into
existing-artifact checks to make the plan pass or publish an instance-only
recovery definition as a verified from-scratch method.

For a new helper outside the current write scope, replan to claim its exact path
before creating it, and freeze its creation as a local-write step with explicit
`source_writes`. A `script_ref` must name a real file when bound. If a helper
was already created, it must have been inside the original authorized scope;
do not retrospectively adopt an unowned write. Retain all accumulated source
changes for the final canonical cognition closeout. Re-read `do show` and its
definition/attempt expansion commands before continuing the new epoch.

## Stable Inputs and Unrelated Concurrent Changes

Require `do.scoped-recovery.v1` before using this contract. Freeze a maintained,
reviewable script with `script_ref`; the runtime also captures recognizable
script-file argv inputs relative to their action cwd. Declare the complete
project/config/resource/tool dependency closure in `source_files`, including
any captured source manifest. An AGENTS-only declaration is not a build-input
closure. Never hide executable script bodies in environment variables; secrets
alone use environment bindings. A changed bound script requires replan or fresh
verification. Public paths and ordinary shell preferences are not secrets;
sensitive errors identify only a JSON pointer and rule, never the rejected value.

Before heavy copying/building, check the required include roots, resources,
fonts, SDK/config, packaging tool, shell version and peak free space for mirror,
build, staging, archive and independent extraction on each affected volume.
Keep Windows PowerShell 5 and PowerShell 7 explicit. Reject insufficient space
before the heavy operation; do not add irrelevant broad tests. Preserve native
process session handles separately from orchestration cell IDs, poll only a
running handle, and parse output only after an actual completed observation.
Unknown side effects still require recovery, never automatic replay.

For exact unrelated workspace changes with no confirmed owner, inspect their
actual diff and the operation's full read/write closure, then submit `do resume`
with `expected_revision`, `external_changes:{"paths":["exact/path"]}` and the
existing typed `recovery` evidence. Omit `attempt_id` and `replan`. This records
a runtime-bound external disposition, not a claim over another Work or an
ignore rule. Runtime rechecks bytes, definition/epoch, source basis and evidence;
a later change requires a fresh inspection. Inputs (including historical read
inputs), own writes/outputs and metadata cannot be excluded. If a blocker was
already recorded, resolve it afterwards with the ordinary fresh-evidence
`do resume` branch; external inspection itself does not clear it.

If concurrent edits affect a consumed input, revalidate/rebuild as required or
bind an actual captured snapshot as the input and prove the delivered artifact
against it. Never relabel changed live inputs as external. This maintenance
capability does not retrospectively authenticate an old environment payload,
complete an unfinished session, or prove an unexecuted reusable method.

## Knowledge Update

Inspect `api show playbook.update` and its input schema before a new mutation.
Update with the exact verified template (`--section method`), matching completed `session_id`,
change summary, and current `base_digest` for an existing playbook. Concurrent
updates require rereading the current revision and reconciling actual semantic
differences. Different targets, owners, variants, or incompatible environments
remain separate methods; do not overwrite one simply because the title matches.

Persist only information that makes the next execution more reliable or less
expensive: authoritative commands, required prerequisites, output checks,
known-good ordering, reusable script references, failure discriminators, and
validated shortcuts with their applicability limits. No-change reuse should
record usage without creating a duplicate revision. A suggestion, partial
failure, or unverified optimization cannot supersede current verified guidance.
To retain a candidate from failed or blocked execution, use its exact
`session_id` and `proposal_only=true`; the runtime registers only the permitted
metadata scope. Do not omit the session to bypass ownership. A saved proposal
does not mark execution passed or complete the session's knowledge disposition.

Keep lessons in Learning when the reusable content is a pitfall, constraint, or
decision rule rather than an operation method. Follow `learning start` policy;
first finish verified execution with knowledge `pending`, then capture any
meaningful signal before the final knowledge disposition. Both automatic and
manual capture bind the exact session: manual `learning capture --command sp-do`
also requires `--session-id <id>` to register its metadata scope. Prefer
`learning capture-auto --command sp-do --session-id <id>` for real session
corrections, failures, or improvements, not routine passing output. Capture only
a meaningful sanitized signal and explicitly review its disposition.
Never auto-promote a lesson or method into a project rule.
