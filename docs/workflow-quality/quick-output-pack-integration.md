# Quick compact-output discovery

## Integrated source paths

Compact-output discovery is available through `quick --help`, `api show`, and
`api pack`, all reusing `quickCompactOutputContract`. The presentation option is
parsed once at the start of `quickService.runExecution`, before project lookup,
packet writes, claims or acceptance. Full output remains the default.

```sh
specify-runtime quick --help --format json
specify-runtime api show quick.item-start --format json
specify-runtime api pack --capabilities quick.item-start,quick.allow-inline,quick.item-accept,quick.item-status --format json
```

Quick help exposes `data.output_contracts`, keyed by the four supported capability
ids drawn from its existing command list. Single-capability `api show` and each
selected `api pack` item expose the same additive `output_contract` with the
producer schema,
standalone boolean flag, fallback behavior, omitted fields, exact compact usage
and a non-mutating full-context refresh command. Existing `usage`,
`input_contract` and `side_effect` fields remain unchanged. A descriptor-owned
output contract, including explicit null, is preserved rather than overwritten.
The existing capability selection and serialized pack-size bounds still apply
**after** this metadata has been added.

Consumers must inspect `output_contract`, not merely assume that a recognized
capability id or capability-set hash proves support for the optional flag.
Discovery may be reused only while the pinned runtime identity is unchanged;
recheck after a runtime upgrade. Begin with full intake. Use compact responses
only while the decision binding remains understood and current. To expand
context, query `quick item-status` without the flag using the same project root;
never replay an item-start, inline approval or acceptance merely to get prose.

The four advertised operations are item-start, allow-inline, item-accept and
item-status. Packet-compile retains historical acceptance of a single
`--compact` flag, but produces the full packet and advertises no compact schema.
The parser rejects repeated flags and `--compact=<value>`. A flag-looking string
that is the value of an existing Quick option (e.g. evidence or reason) is data,
not a presentation request. Invalid presentation options return
`usage-error` / `quick-output-option-invalid` before execution service access.
Other required fields and all authorization/evidence validation remain owned by
the existing command implementation.

## Deliberate rollout boundary

All three discovery entrypoints now advertise the same presentation contract.
This does not broaden execution-time option support: top-level Quick command
families that do not call `runExecution` retain their
old argument behavior. No general argument parser, `--` separator support or
new option-value syntax is introduced. Put the Quick operation and id before
its options as shown by the command's usage.

The previously delivered all-entrypoint discovery patch is superseded for these
files: it uses overlapping helper names and older strict baselines. Do not
apply it on top of this source. The later Help/Show-only pending patch has also
been integrated; do not reapply it. Source integration is not runtime publication.

Advanced SPX Quick's required `references/task-contract.md` now conditionally
opts execution calls into compact output after full intake and per-operation
contract negotiation. It reuses already loaded discovery or replaces the separate
executor query with one Pack request; unsupported discovery/metadata retains full
output. Resume/context loss, changed runtime identity or decision binding, and
scope reconciliation require full read-only status before further writes. A full
fallback is consumed as returned, never retried to force compact presentation.
Returned progress replaces unnecessary follow-up pulse reads.

The decision digest is not a file hash or an execution/permission cache key.
Current packets, claims, executor flags, proofs, blockers and queues must still
be consumed. A transport failure after mutation is not permission to replay it.
Advanced's separate executor selection is described in
[Quick executor selection](quick-adaptive-dispatch.md); `execution_contract` is
not the presentation `output_contract`. No Classic source, runtime default,
installer, existing installation or public distribution is changed here.
This source policy is not an installed-agent or production rollout claim.
No merge, release or public source publication is authorized by this document.

## Persisted execution-state schema

The shipped `quick-confirmation-schema.json` declares the runtime's worker lock,
result ID/reference/lane, execution mode, inline approval/reason, and optional
`blocked_dispatch` audit record. These fields remain optional for legacy and
pre-dispatch documents. Unknown execution fields are still rejected; decision,
UI/source-continuity and delivery contracts are unchanged.

This schema describes persisted state, not permission to author runtime-owned
fields. Passing shape validation does not prove a result exists, verify a digest,
authorize inline execution, or replace Work, acceptance and closeout gates.
`TestQuickConfirmationExecutionSchemaMatchesRuntime` reflects the actual Go
serialization fields; `test_quick_confirmation_execution_schema.py` validates
positive and negative synthetic documents with Draft 2020-12 JSON Schema.
Run both in a complete checkout before consumer rollout.

## Validation

The exact output-contract/parser/projection functions and existing lazy-rendering
tests can be tested without external dependencies:

```sh
GO111MODULE=off go test -race -count=1 -v quick_execution_output.go quick_execution_dispatch.go quick_execution_response.go quick_execution_output_test.go quick_execution_help_test.go quick_execution_lazy_test.go
GO111MODULE=off go vet quick_execution_output.go quick_execution_dispatch.go quick_execution_response.go quick_execution_output_test.go quick_execution_help_test.go quick_execution_lazy_test.go
GO111MODULE=off go test -run '^$' -fuzz '^FuzzQuickOutputLiteralValues$' -fuzztime=3s -parallel=2 quick_execution_output.go quick_execution_dispatch.go quick_execution_response.go quick_execution_output_test.go
```

These tests check the exact supported denominator, producer-schema agreement,
full-context recovery, fresh collections, preservation of existing descriptors,
and flag/value boundaries. They do not execute the complete runtime service.
The package tests in `quick_execution_output_integration_test.go` exercise the
real `Run -> api pack` and `Run -> quick -> runExecution` paths in a complete
checkout, including read-only discovery and early invalid-input failure.
`quick_execution_discovery_consistency_test.go` additionally compares help, show
and both pack variants through the real `Run` routes. It checks help aliases,
unsupported commands and preservation of existing descriptor fields. These
full-package tests must be run in a complete checkout; helper results do not
establish their outcome.

Required before rollout:

```sh
go test -count=1 -run 'TestQuick(Direct|Confirmation|Output|Help|Show|Scope|Queue|Lazy|Compact|Resume)' .
go test -count=1 ./...
go vet ./...
```

A helper pass is not a complete runtime, Work/SQLite, installed-profile, cloud
CI or real-agent pass. This increment supplies no measured production token,
latency or quality-retention percentage.

## Consumer-policy regression coverage

`quick_compact_consumer_contract_test.go` checks the required SPX reference's
negotiation anchors against the actual shared producer metadata, and preserves
full-intake, recovery and authority boundaries. It is a source/producer contract
test, not an interpreter or an evaluation of model instruction following.

`quick_compact_consumer_integration_test.go` exercises worker and direct execution
with full and compact responses using the real Work/Quick fixtures and
`result submit` route. Each scenario starts once, refuses missing result evidence,
submits a synthetic successful result, accepts once and queries full/compact
status without replaying a mutation. It compares every non-omitted data field and
checks confirmation/STATUS bytes remain unchanged across read-only refreshes.
Reported check statuses in these fixtures do not prove product checks ran.

Run the full-package test in a complete checkout:

```sh
cd tools/specify-runtime
go test -count=1 -run '^TestQuickCompactConsumer' .
```

Before distributing the policy, also run full Go/Python/lint and installed
Classic/Advanced rendering/upgrade tests, including older-runtime fallback.
A standalone source-contract pass does not establish full-package, installed
consumer, Work/SQLite, cloud CI, real-agent behavior or token savings.

## Complete-checkout verification entrypoint

`tools/workflow-quality/verify_quick_rollout.py` is developer tooling, not a
workflow stage or installed runtime dependency. Run it from a clean, isolated,
complete Git checkout with the matching Go toolchain/dependencies already cached
and a Python environment containing this checkout of `specify_cli`, test extras,
pytest-xdist and Ruff. It does not prepare or install that environment.

```sh
python tools/workflow-quality/verify_quick_rollout.py --output-dir ../quick-rollout-evidence
```

The output directory must be new, have an existing parent and be outside the
checkout. The runner never resets local modifications or overwrites prior
reports. It checks tracked-file presence, a clean source revision and the Python
import origin; performs an offline Go dependency preflight; then executes the
complete Go tests, Go vet, complete Python tests and the existing CI Ruff scope.
Child Go commands use `GOWORK=off`, `GOTOOLCHAIN=local`, `GOPROXY=off` and
`GOFLAGS=-mod=readonly`. Existing test code can spawn its own subprocesses; this
runner is not a sandbox, an offline-network enforcement boundary or a guarantee
that tests have no side effects. Per-command timeouts terminate the process group
on POSIX and attempt process-tree cleanup on Windows.

Exit codes: `0` means the requested checks passed, `1` means a completed gate
failed, and `2` means validation was blocked/incomplete. Read `summary.json` and
per-command stdout/stderr logs for the exact scope. Go JSON must contain actual
passing terminal events for the named Quick lifecycle tests, including all four
worker/direct x full/compact scenarios. Pytest JUnit must contain all seven named
installation/repair cases from `test_quick_optimization_installation.py`, passed
rather than skipped. Empty selection, missing tests, malformed reports, wrong
module identities or a changed source revision cannot produce a green result.
Other platform skips are counted explicitly. A successful subprocess exit alone
is insufficient.

The new installation tests call the real integration setup/repair owners for
Codex and Cursor, including sh/ps rendering, Classic default isolation, missing
policy restoration and preservation of user modifications. They do not invoke
an actual model, exercise every host, prove a released binary upgrade, or replace
an independent acceptance/cost evaluation. Runner unit tests include synthetic
reports and tiny real Go/pytest fixtures; those tests do not establish a product
runtime or installation pass. A runner pass is never merge/release authorization.
Logs may contain private test output; inspect them before sharing. No upload,
telemetry, source publication, Git mutation or release is performed by the runner.
