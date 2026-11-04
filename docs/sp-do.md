# sp-do: reusable project operations

`sp-do` runs a concrete project operation and preserves the verified method for
the next request. Use it for compiling, packaging, tests, file operations,
browser or desktop tasks, and connector operations within the authorized project
scope and the agent's available tools. Advanced
provides the independently authored `spx-do` skill over the same Go protocol.

The user supplies an outcome in ordinary language. The agent finds a relevant
method, checks it against current source and tools, executes through native
tools, verifies the result, and improves the same method when it has learned
something reusable. First use needs neither a Playbook nor a feature workspace.

## User-facing entrypoints

For Codex:

```text
$sp-do package this project and verify the generated package
$sp-do run the same regression suite again after this change
$spx-do rebuild the CLI and preserve useful commands and checks for next time
```

Other integrations use their native command spelling; follow the installed
catalog. Both profiles accept natural-language goals. Users do not need to
author session JSON themselves.

When several Do sessions belong to the same integration, select the requested
session explicitly with the native invocation suffix `resume <session-id>`, for
example `/sp-do resume first-use` in Claude or `$spx-do resume first-use` in
Codex. Hooks verify that exact runtime session rather than choosing the latest
or another unfinished session. The runtime rejects a repeated `do start` from
a different caller or adapter; use the guarded resume/recovery route for an
existing Work owner.

This is an explicitly invoked workflow. It adds no passive router and does not
advance `specify -> plan -> tasks -> implement -> review -> accept`. Quick,
Implement and E2E may retrieve a relevant method through `playbook find/show`.

Each workflow retains its own Work, validation ledgers and acceptance gates.

## Knowledge boundaries

| Surface | Question answered | Owner |
| --- | --- | --- |
| Project memory/rules | What constraints govern this project? | Existing memory and rule owners |
| Project Learning | Which pitfall, recovery principle or decision should be recalled? | `specify-runtime learning` |
| Project cognition | Where does behavior live, and which source paths changed? | Existing cognition protocol |
| Project Playbooks | How is this recurring operation performed and verified? | `specify-runtime playbook` |
| DoSession | What happened during this invocation? | `specify-runtime do` |

Methods reference Learning and maintained scripts. Ordered steps, applicability
and required checks belong to the method. Attempts, timing, native observations
and recovery evidence belong to the invocation. Ordinary successful reuse does
not create another generic lesson or repeat the whole guide.

## Progressive disclosure

1. Start with `learning start --command sp-do` and a bounded `playbook find`.
   Narrow candidates using the observed operation, target, toolchain context and
   actual parameter values.
2. Read the selected summary and source references. Follow its pinned `show_argv`
   and expand only the needed steps, checks or evidence section.
3. Inspect current scripts/configuration and prerequisites. A previous success
   is a useful route; the current invocation still needs its own verification.
4. Freeze the full definition for the current execution plan. Session reads
   remain compact; definitions, previous plan versions and individual attempts
   are explicit expansions.

`playbook find` defaults to five cards and supports at most twenty per page with
a continuation cursor. It matches normalized words, canonical operation names
and explicit aliases, including multilingual aliases. Applicability filters use
observed context. Missing or incompatible context and changed source fingerprints
remain visible. No embedding service or new database is required.

Identity is derived from operation, target, owner and variant. A changed title
does not create a new identity. Use separate variants for incompatible modes.
Current verified methods take precedence over proposals; a first-use proposal is
also discoverable, clearly unverified and pinned by its digest when expanded.
An existing method's summary exposes one pending proposal based on its current
digest, with an exact expansion command. Select and verify that candidate during
a later invocation before promoting the improvement.

## Execution and persistence lifecycle

| Phase | Operation | Required result |
| --- | --- | --- |
| Select | `playbook find/show/validate` | Current method or explicit first-use definition |
| Prepare | `do prepare` | Read-only canonical `start_input`, template/instance digests and source basis |
| Freeze | `do start` | Rechecked exact definition, parameters, scope, session and Work fence |
| Next action | `do next` | Ready full actions, started input and incomplete observation skeletons |
| Execute/checkpoint | Native tools and `do record` | Recorded start, actual completion or interruption, required effect checks |
| Verify | `do validate` | All frozen required steps/checks and applicable source closeout |
| Ordinary closeout | `do complete` | Validated execution, exact-template revision/usage and saved knowledge |
| Explicit closeout | `do finish` pending, scoped Learning if meaningful, `playbook update`, `do finish` saved | Same owners with a lesson, manual publication or an explicit alternative disposition |

Rejected JSON fields in `do prepare`, other Do inputs and Playbook inputs include
`data.validation_errors`: each entry has an RFC 6901 `instance_path` such as
`/definition/checks/0/argv`, a `keyword` such as `required`, `type` or
`additionalProperties`, and a message without submitted values. Prepare input
failures also return `data.schema_argv`; correct the input and retry preparation.
An initial validation failure creates no DoSession or Work and is not a session
resume operation. Process-based checks require `cwd` and `argv` even when they
only inspect an artifact: use `"cwd":"."` and `"argv":[]` for those checks.
An `exit_code` check instead requires a nonempty command. `source_writes`
belongs to a `local_write` step, not to a check.

Go owns generated state, validation, artifact registration and transactions.
Python owns bootstrap, installation, native integration rendering and
compatibility. The runtime never launches the build/test command. Observations
retain `evidence_origin=agent_tool_observation` and explicitly report
`runtime_execution_verified=false`.

Send prepare's `start_input` to `do start`; preparation alone creates no Work or
session and does not freeze changing conditions. `do next` supplies full frozen
actions and known recording fields. Record `started_input` before the selected
action, fill `completion_event` with actual `completion_required` facts, and
submit it through `do record` with the latest revision and a unique request ID.
Refresh next after each checkpoint: its ready entries share one revision.
`running` identifies attempts to observe or recover, never imaginary success.

Process observations retain the real handle, argv/cwd, timestamps, tool-call
identity, exit result and output references. File/browser/desktop/connector
actions retain their typed action and actual JSON observation instead; do not
invent process fields. Completion cannot create its start retrospectively.
Timeout, cancellation and unknown native outcomes remain interrupted.

Dependencies bind to concrete attempts. After a producer runs again, its
consumers must check the new result. Required checks establish the promised
output: package existence/metadata, a structured success field or the expected
test denominator. Historical snapshots remain evidence of the past; current
required output paths must still match before a current success claim.

When `do next` returns `complete_ready`, add a truthful `change_summary` to its
`complete_input` and use `complete_argv`. This composes the existing execution
finish, template publication and saved-knowledge finish; it does not run tools
or skip validation/source closeout. A publication error leaves passed execution
with pending knowledge. Reread the revision and retry without rerunning the
successful operation. Completion replay does not duplicate usage. Require a
terminal result; readiness alone is not completion.

## API discovery

Use the project-pinned runtime returned by the installed launcher. Discover
capabilities and schemas before composing mutations:

```sh
specify-runtime api pack --capabilities do.prepare,do.start,do.next,do.record,do.complete,do.resume --include-schema --format json
specify-runtime api show do.validate --format json
specify-runtime api schema playbook-definition-input --format json
```

The fourteen capabilities are `do.start`, `do.record`, `do.validate`, `do.finish`,
`do.resume`, `do.show`, `playbook.find`, `playbook.show`, `playbook.update` and
`playbook.validate`, plus `do.prepare`, `do.next`, `do.complete` and
`playbook.metrics`. Installers require the entire set.

| Mutation | Schema and contract |
| --- | --- |
| `do prepare --input-json` | `do-prepare-input`: read-only canonical start contract; returns the template and resolved parameter bindings |
| `do start --input-json` | `do-start-input`: template, actual parameters, agent/adapter identity, optional session ID, method binding and scopes |
| `do record <id> --input-json` | `do-record-input`: expected revision, request ID and bounded event batch |
| `do complete <id> --input-json` | `do-complete-input`: expected revision and change summary; verified publication and terminal knowledge |
| `do finish <id> --input-json` | `do-finish-input`: expected revision, knowledge disposition/receipt or evidenced external blocker |
| `do resume <id> --input-json` | `do-resume-input`: expected revision, exact attempt/recovery evidence, optional typed replan and supported Work recovery binding |
| `playbook update --input-json` | `playbook-update-input`: definition, change summary, optional base digest, session and proposal-only disposition |

JSON mutations accept inline objects or `-` for UTF-8 standard input. Prefer
standard input for substantial or quoting-sensitive payloads. Runtime schemas
are authoritative; do not invent flags or edit generated state. Duplicate keys,
unknown fields and invalid nested method shapes are rejected.

Useful reads:

```sh
specify-runtime playbook find --query "package demo" --operation package --limit 5 --format json
specify-runtime playbook show --id <method-id> --revision <revision> --section steps --format json
specify-runtime playbook show --id <method-id> --section evidence --format json
specify-runtime playbook show --id <method-id> --section recovery --format json
specify-runtime playbook metrics --id <method-id> --parameters-json '{"output":"out/package"}' --format json
specify-runtime do next <session-id> --format json
specify-runtime do show <session-id> --format json
specify-runtime do show <session-id> --section method --format json
specify-runtime do show <session-id> --section metrics --format json
specify-runtime do show <session-id> --section definition --format json
specify-runtime do show <session-id> --section definitions --format json
specify-runtime do show <session-id> --section definition:1 --format json
specify-runtime do show <session-id> --section attempt:<attempt-id> --format json
```

`do show --active` resolves live Work Board bindings; `--adapter-id <id>` narrows
that lookup to an integration. Multiple matches are an ambiguity blocker;
directory timestamps are never a selector. An exact ID is required when the
host/workflow cannot identify one unambiguous operation.

## Reusable method definition

A method contains identity, goal, title, aliases, applicability, project-relative
source references, ordered steps, required checks and Learning references.
Steps explain purpose, dependencies, expected result and side effect. Process
steps use cwd/argv; a nonprocess `native_action` uses kind
`file|browser|desktop|connector`, tool, target and JSON arguments, excluding
argv/cwd/script_ref.
Use `script_ref` for maintained scripts so their actual bytes participate in
freshness. Explicit source-mutating steps additionally declare `source_writes`
within their authorized source scope.

| Check kind | Verification |
| --- | --- |
| `exit_code` | The observed native command completed successfully |
| `file` | A real nonempty file and its content hash remain valid |
| `json` | A bounded JSON report matches the expected value at its declared pointer |
| `junit` | The report meets the minimum test count without hidden nonpassing cases |
| `observation` | A separate native call returns JSON matching the frozen pointer and expected value |

"Tests looked good" cannot replace these obligations. Checks and required
denominators are frozen before execution. Changing a check or adding a shortcut
creates a changed definition needing verified execution before publication.

A native mutation in the required dependency closure needs a dependent required
observation/file/JSON/JUnit effect check. Its fresh tool call must follow the
exact producer; a mutation's success response is not its own effect check.
Record `native_observation` with `outcome=succeeded|failed|unknown` and the actual
sanitized JSON `result`. Runtime binds and hashes its snapshot. Observed remote
state is evidence as of that call, not a perpetual current-state guarantee.

### Parameterized methods

Declare nonsecret variable inputs in `parameters`: kind `path`, `enum` or
pattern-constrained `string`, required flag, example, and optional default or
bounds. Optional parameters require a default. A token such as
`{{param:output}}` can fill supported value fields, including native target/JSON
string values. In argv it must fill an entire non-executable argument; shell
command interpolation is rejected. Supply actual strings in `do prepare/start`
`parameters` and concrete resolved write/output scopes. Unknown, invalid or
sensitive values are rejected; parameters do not grant additional authority.

The reusable template digest and this invocation's resolved instance digest
remain separate. `do show --section method` returns the template and bindings;
`--section definition` returns the executable instance. Manual `playbook update`
must use the former's `method_definition`; `do complete` selects it automatically.
Different parameter values reuse unchanged canonical bytes and method revision.
An optional stable `task_family` groups related methods without merging their
distinct instance costs or weakening required checks.

### Measured selection and recovery guidance

`playbook find` defaults to lexical relevance without a session scan. Opt into
`--rank observed` when comparisons justify its cost, supplying complete observed
OS/architecture/shell/toolchain context and the intended `--parameters-json`.
The runtime compares only equal-relevance candidates with equivalent family,
workload, actual parameters, environment, source basis and verification. It
orders observed first-pass reliability before median successful tool time.
At least three eligible invocations are required; timing comparisons additionally
need three successful timing samples. Insufficient timing samples retain their
reliability-sorted slots. Missing, stale or incompatible evidence does not
establish a preferred method, and no ranking claims universal optimality.

Use `specify-runtime playbook metrics --id <id>` and
`specify-runtime do show <id> --section metrics` for runtime-derived observations.
These read-only owner routes create no second statistics database and distinguish resumable current
status, terminal completion, failures, interruption, blocked episodes, retries,
retained evidence and observed durations. Successful usage is not a success-rate
denominator. Mixed epochs and external blocks are excluded from first-pass
comparison; retained receipts do not fabricate new attempts. Tool durations can
overlap and exclude unobserved agent exploration or thinking. Scanning costs
grow with the number of sessions and are reported explicitly.

`playbook show --section recovery` discloses currently validated recovery pairs:
failure discriminators, failed/verified actions, native evidence hashes and
candidate preflights. Match the current failure/context before reuse. Recovery
does not prove a cause or preventive benefit; candidates require current frozen
execution and required checks before verified publication. Expired evidence is
reported and excluded. Learning capture preserves the same distinctions.

Preserve what reduces future discovery: maintained entrypoints, necessary
prerequisites, correct ordering, failure discriminators, validated shortcuts and
their limits, and helper-script references. Keep raw logs and unchanged source
out of the reusable guide. Secrets and machine/account-specific sensitive values
must not be embedded in reusable commands or evidence.

## Stored authority and evolution

| Project-relative path | Meaning |
| --- | --- |
| `.specify/playbooks/<id>/playbook.json` | Current verified method authority |
| `.specify/playbooks/<id>/PLAYBOOK.md` | Derived readable guide |
| `.specify/playbooks/index.json` | Derived compact catalog |
| `.specify/playbooks/<id>/revisions/<revision>.json` | Immutable version history |
| `.specify/playbooks/<id>/proposals/<digest>.json` | Unverified proposed definition |
| `.specify/playbooks/<id>/usage/<session-id>.json` | Execution-bound usage and knowledge receipt |
| `.specify/do/sessions/<id>/session.json` | Invocation state |
| `.specify/do/sessions/<id>/baseline.json` | Immutable whole-workspace change baseline bound by SHA-256 |
| `.specify/do/sessions/<id>/definitions/<epoch>.json` | Immutable plan snapshots materialized on replan |
| `.specify/do/sessions/<id>/evidence/` | Runtime-owned report snapshots, file-hash receipts and inline recovery records |

The readable guide and index are projections, not edit surfaces. Generic
artifact prepare/patch/delete cannot bypass the specialized owner. Changing an
index cannot turn an unverified method into authority.
Other workflow cognition routes cannot write or replay Do-owned session receipts.

New Do sessions use `spec-kit-do-session-v2`: `session.json` stores the exact
`baseline_ref` and `baseline_sha256`, while `baseline.json` retains every initial
Git change path and its content digest. Both files publish atomically. The
checkpoint keeps its 8 MiB limit; the separate baseline has a 64 MiB safety limit,
so unrelated changes in a large workspace do not fill the operation checkpoint.
Missing, redirected or changed baselines block loading and checkpoint writes.
Complete workspace auditing still detects out-of-scope writes, including changes
to files that were already dirty before the session. Size checks run before Work
registration, so deterministic size failures leave no operation claim. Existing
v1 inline-baseline sessions remain resumable; older runtimes reject v2 sessions
before changing them. Both `sp-do` and `spx-do` use this shared storage contract.

Updates compare `base_digest`, preserve immutable revisions and validate the
exact definition against its DoSession. Publication is an atomic file
transaction with method and session preconditions. Conflicts require rereading
and reconciling semantic differences; ordered commands are never silently merged.

Repeated unchanged success adds one idempotent usage receipt without revising
method content or growing the guide. A verified improvement advances the same
method ID. An unexecuted idea or a useful finding from a failed invocation may be
saved as an explicitly unverified proposal, with its own exact Work scope. It
cannot supersede current verified guidance.

These are project-local records preserved by installation and repair. They imply
no automatic export, public publication, rule promotion or retention deletion.
Follow project version-control policy when sharing methods; `.specify/` is
ignored by this source repository.

## Failure, interruption and recovery

Failed attempts are retained. Inspect and repair their concrete cause before
retrying, and record recovery evidence. Interrupted/disconnected commands also
require confirmation that their prior process has stopped and their effects
have been inspected. Runtime recovery does not rerun the command itself.

Every interrupted attempt in the session must be explicitly recovered before
`do validate`, `do finish` or `playbook update` can pass. This includes optional
steps/checks, superseded attempts and earlier definition epochs; a later success
does not clear their unknown effects. Once recovered, an optional attempt need
not be rerun unless a frozen required dependency needs its result.

### Recovery evidence

For ordinary recovery, failed-method replanning and blocker resolution through
`do resume`, supply a nonempty `recovery.reason` and `side_effects_inspected=true`,
plus `processes_stopped=true` for a process or `native_action_settled=true` for
a nonprocess action (both for mixed-operation recovery), and exactly one evidence form:

- `evidence_ref`: an existing sanitized evidence file inside the session's
  already declared `write_scope` or `output_scope`. A new scope in the same
  replan does not authorize prewriting that file.
- `evidence_text`: a nonempty sanitized UTF-8 record, at most **64 KiB in bytes**,
  of process termination or native action settlement and the observed side-effect inspection. The
  runtime atomically stores it with the recovery/session revision check under
  the session's existing Work-owned `evidence/` directory. Do not prewrite or
  hand-edit that protected directory. Inline evidence adds no source/output
  permissions and does not perform the native inspection on the agent's behalf.

Never supply `evidence_sha256`; the runtime derives the digest. Record actual
process and inspection observations, not a presumed absence of side effects.

For example, a failed read-only check can recover without adding scopes or
creating a log file. For a session started with `write_scope=[]` and
`output_scope=[]`, the agent submits the following shape to
`do resume <session-id> --input-json -` after the native inspections. Replace
the illustrative revision, attempt ID and observation with the current values:

```json
{
  "expected_revision": 7,
  "attempt_id": "inspect-env-1",
  "recovery": {
    "reason": "The read-only check failed; its process and effects are reconciled.",
    "evidence_text": "Native process check-17 exited with code 1 and has no remaining child process. Fresh read-only Git status matches the pre-check state; no files or external systems changed.",
    "processes_stopped": true,
    "side_effects_inspected": true
  }
}
```

### Failed-method replanning

If the command or plan itself must change after an observed failure, use typed
`do resume` with `replan.request_id` and the replacement `replan.definition`,
along with the exact failed `attempt_id`, `expected_revision` and `recovery`
evidence in either form above. Optional `replan.write_scope` and
`replan.output_scope` inherit when omitted; supplied scopes preserve existing
claims and may add authorized paths before their first mutation. Scope changes
cannot retroactively absorb writes.

Replanning preserves the original goal, method identity, failed observations and
immutable plan history. Each plan has a runtime-owned `definition_epoch`.
By default required actions need new observations in that epoch. Active or unknown effects must be
recovered first. A passed operation with pending knowledge repairs persistence
through its existing receipt rather than opening another execution plan.

To adapt an action before it starts, use `replan.mode="unstarted"` with no
`attempt_id` or `recovery`. Only unattempted actions may change; a fictitious
failure is unnecessary. Either mode can request `retain_verified=true` to reuse
eligible original process observations through a verified immutable epoch chain with unchanged actions,
source basis and dependency bindings, backed by freshly rehashed local results.
The full required dependency closure, outcome assertions and edges remain
fixed. Native/external actions, source writers and broken evidence chains are
excluded. New required checks run, and local outputs are rechecked before a new
consumer starts. Retained receipts point to original observations; they neither
rewrite history nor count as new executions. Every retained hop must remain verified; a missing hop invalidates reuse.

### Resumable persistence and blockers

Creation is idempotent for an explicit session ID with identical frozen input.
Event batches use request IDs: replay returns the same checkpoint; the same ID
with a changed payload is rejected. Replan has its own request ID and immutable
receipt. Finish and ordinary resume use exact state/receipt replay and revision
checks.

If publication fails after a successful build, keep execution `passed` and
knowledge `pending`. Repair only persistence, revalidate the retained evidence,
and retry `do complete` or the explicit update/finish path. No native command is replayed by that recovery. If
sources or required outputs have since changed, resolve freshness before
claiming the prior result remains current.

Real human/external blockers may be recorded with category, owner, concrete
cause, attempted recovery, exact evidence, next action, unblock criteria and
resume point. An accepted blocker permits an honest exit with `can_stop=true`
while `terminal=false`. It creates neither success nor a knowledge receipt.
Agent-repairable problems remain in the active loop.

Resolve an accepted blocker through `do resume` with fresh recovery evidence in
either form above. This does not change the scoped file-reference contract of
`do finish`'s `blocker.evidence_refs`, or silently recover a separate interrupted
attempt.

Work lease recovery is explicit. Preserve the operation identity and use the
current fence from an actual Work recovery. A method or old receipt never grants
permission to take another owner's scope or bypass external side-effect gates.

## Learning and source closeout

Do recalls older project-wide Learning defaults that predate its command name,
without rewriting stored entries or widening explicitly narrow preferences.
Existing operation-owner/facet recall supports related cross-workflow lessons.

After execution finishes with knowledge pending, use
`learning capture-auto --command sp-do --session-id <id>` for verified recovery
signals. Normal passing output is a no-op. A specific manually distilled lesson
uses `learning capture --command sp-do --session-id <id>` and normal Learning
fields. Learning holds the Do session lock before the Learning lock, registers
exact planned files on the same Work, and retains that ownership through the
write. Its metadata is not classified as product source. Promotion remains
explicit.

Use the explicit finish-pending branch when a lesson is warranted, capture it,
then call complete from a fresh revision or continue manual update/finish.
Ordinary complete does not create a lesson merely because the operation passed.

Authorized source/script/configuration changes require canonical `sp-do`
cognition closeout with actual changed paths and exact session scope. Follow the
existing planner-first cognition route and receipt contract. The runtime freezes
the Do source and definition epoch into the existing cognition intent before
refreshing the graph; its receipt retains that binding. The cognition writer
claims its exact database, status, receipt and intent paths on the same Work.
Current source must still match when the refresh is finalized and Do completes.
A pending cognition intent for this session must finish its guarded recovery
before Do can publish knowledge and release Work, even if a ready receipt exists.
Retry the exact Do-bound replay route returned by the runtime. Another workflow
cannot automatically drain a pending Do intent: replay acquires the matching Do
session lock before the cognition lock and rechecks the session, epoch and source
binding. Other workflows retain their own existing recovery routes.

Pure outputs and registered method/Learning metadata record cognition as not
applicable. An operation must neither absorb another owner's changes nor hide undeclared
source writes in output scope.

Source-mutating steps record their authorized writes and source transition;
final nonmutating checks bind to the resulting source. Adding a helper or
changing a method still requires freezing and verifying the resulting method.
An old successful definition cannot bless newly written commands.

## Reproducible acceptance probe

[do_operation_probe.py](../tests/e2e_samples/do_operation_probe.py) creates a new
isolated Git project, runs a Python ZIP builder/verifier through actual native
subprocesses, and records file observations through the public Go CLI:

```sh
python tests/e2e_samples/do_operation_probe.py --runtime <built-runtime> --project <new-isolated-directory>
```

It covers first publication, synonymous bounded recall, unchanged reuse,
verified compression improvement, immutable history, idempotent knowledge
replay, stale revision rejection and current-report tampering. Its method
revisions are `1, 1, 2`. Timing and archive sizes are measured observations from
that run, not a promise of universal speedup.

[do_optimization_probe.py](../tests/e2e_samples/do_optimization_probe.py) adds
three real packaging invocations with one unchanged template/revision and
distinct parameter instances, plus a full-replan/manual-closeout control. It
checks that retaining three validated local observations runs only the newly
added check, while the control executes all four new-epoch actions. It measures
actual public calls for complete versus explicit finish/update/finish, verifies
unchanged canonical method bytes, and reports each adapter episode's elapsed
time. These are local fixture observations, excluding model thinking and any
claim of general speed or accuracy improvement.

The integration test uses the same probe with the built runtime:

```sh
uv run pytest tests/test_do_operation_probe.py tests/test_do_optimization_probe.py tests/test_do_hooks.py tests/test_do_launcher.py tests/integrations/test_do_installation.py
```

Go tests cover evidence, recovery, evolution, Learning, API discovery, Work
claims and specialized artifact ownership. They also exercise an actual failed
native command followed by typed replan and method publication, and real source
generation followed by full cognition refresh and bound closeout. Integration
tests cover both profiles, native rendering, Shell/PowerShell templates, both additive install
orders, retained user edits, repair and wheel consumption.

## Installation and distribution

Classic adds one command; Advanced adds one skill. The catalog now has 29
Classic commands and 30 SPX skills, including Advanced's map rebuild. Advanced
still installs only its three intentional Classic map companions and does not
install the Classic passive bundle.

The Python launcher and both standalone installers require all fourteen Do
capabilities. An older runtime is rejected instead of being accepted because a
prompt exists. Schemas/references ship through the existing template package;
repair preserves project data and edited native skills in either install order.

Source changes and local tests do not publish a runtime release. Follow
[Public runtime distribution](runtime-release-distribution.md) for matching
version/source identity, platform binaries, checksums and anonymous consumer
verification. The source repository remains private.

## Script bindings and concurrent recovery

The `do.scoped-recovery.v1` capability versions public-script diagnostics,
script-file input capture, audited unrelated changes and verified epoch-chain
retention. Keep executable helpers in reviewable project files; use `script_ref`
and complete `source_files`, including project/config/resource dependencies.
Recognizable script argv files are captured relative to cwd; environment-held
script bodies are rejected rather than treated as frozen code. Secrets retain
environment bindings, and diagnostics omit their values.

`do resume` can record `external_changes:{"paths":["exact/path"]}` with current
revision and typed recovery evidence, separately from attempt recovery/replan.
This audits current unrelated differences without claiming their ownership,
widening scope, changing the baseline or excusing consumed-input changes.
Byte/source/epoch/evidence drift invalidates it. Resolve an already recorded
blocker with the normal fresh-evidence resume afterwards. Unchanged process
results can retain original attempts through every verified epoch hop; no new
execution/timing is invented and changed dependencies invalidate reuse. Do not
publish instance-only artifact rechecks as verified from-scratch build methods.

Preflight exact shell/tool versions, dependency closure and each volume's peak
mirror/build/staging/archive/extraction space before heavy work. Native process
handles and orchestration cells are separate; interrupted effects are inspected
before any retry. These checks do not require repeating a real installer or
running a broad test matrix.
