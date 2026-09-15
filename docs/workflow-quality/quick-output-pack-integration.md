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

Generated consumers are not automatically opted into compact output. Advanced's
separate capability-gated executor selection is described in
[Quick executor selection](quick-adaptive-dispatch.md); `execution_contract` is
not the presentation `output_contract`. Classic delegated defaults, installation,
public distribution and cross-stage execution remain unchanged. No merge, release
or public source publication is authorized by this document.

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
