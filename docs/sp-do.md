# sp-do: reusable project operations

`sp-do` runs a concrete project operation and preserves the verified method for
the next request. Use it for compiling, packaging, running an existing test
suite, checking an environment, or maintaining a bounded project tool. Advanced
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
   Narrow candidates using the observed operation, target and toolchain context.
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
| Freeze | `do start` | Exact definition, source basis, scope, session and Work fence |
| Execute | Native process/file tools | Actual completion or observed interruption |
| Checkpoint | `do record` | Start checkpoint followed by observations for the same attempt |
| Verify | `do validate` | All frozen required steps/checks and applicable source closeout |
| Close execution | `do finish`, knowledge `pending` | Execution passed; knowledge remains resumable |
| Preserve lessons | Scoped `learning capture-auto/capture` | Meaningful candidates; no automatic promotion |
| Preserve method | `playbook update` | Verified revision, no-change usage, or unverified proposal |
| Close knowledge | `do finish` with the returned receipt | Terminal invocation and completed Work |

Go owns generated state, validation, artifact registration and transactions.
Python owns bootstrap, installation, native integration rendering and
compatibility. The runtime never launches the build/test command. Observations
retain `evidence_origin=agent_tool_observation` and explicitly report
`runtime_execution_verified=false`.

Checkpoint `started` before launching a native command. Retain its process
handle, wait for actual completion, and record its real argv, cwd, timestamps,
tool-call identity, exit result and output references. Completion cannot create
its start retrospectively. Timeout and cancellation remain interrupted.

Dependencies bind to concrete attempts. After a producer runs again, its
consumers must check the new result. Required checks establish the promised
output: package existence/metadata, a structured success field or the expected
test denominator. Historical snapshots remain evidence of the past; current
required output paths must still match before a current success claim.

## API discovery

Use the project-pinned runtime returned by the installed launcher. Discover
capabilities and schemas before composing mutations:

```sh
specify-runtime api pack --capabilities do.start,do.record,do.finish,do.resume,playbook.update --include-schema --format json
specify-runtime api show do.validate --format json
specify-runtime api schema playbook-definition-input --format json
```

The ten capabilities are `do.start`, `do.record`, `do.validate`, `do.finish`,
`do.resume`, `do.show`, `playbook.find`, `playbook.show`, `playbook.update` and
`playbook.validate`. Installers require the entire set.

| Mutation | Schema and contract |
| --- | --- |
| `do start --input-json` | `do-start-input`: definition, agent/adapter identity, optional session ID, method binding and scopes |
| `do record <id> --input-json` | `do-record-input`: expected revision, request ID and bounded event batch |
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
specify-runtime do show <session-id> --format json
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
Steps explain purpose, cwd, argv, dependencies, expected result and side effect.
Use `script_ref` for maintained scripts so their actual bytes participate in
freshness. Explicit source-mutating steps additionally declare `source_writes`
within their authorized source scope.

| Check kind | Verification |
| --- | --- |
| `exit_code` | The observed native command completed successfully |
| `file` | A real nonempty file and its content hash remain valid |
| `json` | A bounded JSON report matches the expected value at its declared pointer |
| `junit` | The report meets the minimum test count without hidden nonpassing cases |

"Tests looked good" cannot replace these obligations. Checks and required
denominators are frozen before execution. Changing a check or adding a shortcut
creates a changed definition needing verified execution before publication.

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
| `.specify/do/sessions/<id>/definitions/<epoch>.json` | Immutable plan snapshots materialized on replan |
| `.specify/do/sessions/<id>/evidence/` | Immutable report snapshots or compact file-hash receipts |

The readable guide and index are projections, not edit surfaces. Generic
artifact prepare/patch/delete cannot bypass the specialized owner. Changing an
index cannot turn an unverified method into authority.

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

If the command or plan itself must change after an observed failure, use typed
`do resume` with `replan.request_id` and the replacement `replan.definition`,
along with the exact failed `attempt_id`, `expected_revision` and `recovery`
receipt. Optional `replan.write_scope` and `replan.output_scope` inherit when
omitted; supplied scopes preserve existing claims and may add authorized paths
before their first mutation. Scope changes cannot retroactively absorb writes.

Replanning preserves the original goal, method identity, failed observations and
immutable plan history. Each plan has a runtime-owned `definition_epoch`.
Every required step/check needs new observations in that epoch, even when a
later plan returns to an earlier definition. Active or unknown effects must be
recovered first. A passed operation with pending knowledge repairs persistence
through its existing receipt rather than opening another execution plan.

Creation is idempotent for an explicit session ID with identical frozen input.
Event batches use request IDs: replay returns the same checkpoint; the same ID
with a changed payload is rejected. Replan has its own request ID and immutable
receipt. Finish and ordinary resume use exact state/receipt replay and revision
checks.

If publication fails after a successful build, keep execution `passed` and
knowledge `pending`. Repair only persistence, revalidate the retained evidence,
and replay update/finish. No native command is replayed by that recovery. If
sources or required outputs have since changed, resolve freshness before
claiming the prior result remains current.

Real human/external blockers may be recorded with category, owner, concrete
cause, attempted recovery, exact evidence, next action, unblock criteria and
resume point. An accepted blocker permits an honest exit with `can_stop=true`
while `terminal=false`. It creates neither success nor a knowledge receipt.
Agent-repairable problems remain in the active loop.

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
fields. Learning registers exact planned files on the same Work before writing;
its metadata is not classified as product source. Promotion remains explicit.

Authorized source/script/configuration changes require canonical `sp-do`
cognition closeout with actual changed paths and exact session scope. Follow the
existing planner-first cognition route and receipt contract. The runtime freezes
the Do source and definition epoch into the existing cognition intent before
refreshing the graph; its receipt retains that binding. The cognition writer
claims its exact database, status, receipt and intent paths on the same Work.
Current source must still match when the refresh is finalized and Do completes.
A pending cognition intent for this session must finish its guarded recovery
before Do can publish knowledge and release Work, even if a ready receipt exists.

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

The integration test uses the same probe with the built runtime:

```sh
uv run pytest tests/test_do_operation_probe.py tests/test_do_hooks.py tests/test_do_launcher.py tests/integrations/test_do_installation.py
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

The Python launcher and both standalone installers require all ten new
capabilities. An older runtime is rejected instead of being accepted because a
prompt exists. Schemas/references ship through the existing template package;
repair preserves project data and edited native skills in either install order.

Source changes and local tests do not publish a runtime release. Follow
[Public runtime distribution](runtime-release-distribution.md) for matching
version/source identity, platform binaries, checksums and anonymous consumer
verification. The source repository remains private.
