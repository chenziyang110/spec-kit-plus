# Quick compact-output batch discovery

## Integrated source paths

This increment connects compact-output discovery through `api pack` and parses
its presentation option once at the start of `quickService.runExecution`, before
project lookup, packet writes, claims or acceptance. It builds on the existing
opt-in response projection; full output remains the default.

```sh
specify-runtime api pack --capabilities quick.item-start,quick.allow-inline,quick.item-accept,quick.item-status --format json
```

Each selected item has an additive `output_contract` with the producer schema,
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

This is batch discovery, **not** the earlier all-entrypoint discovery proposal.
`api show` and `quick --help` have not been changed to advertise compact output.
Top-level Quick command families that do not call `runExecution` retain their
old argument behavior. No general argument parser, `--` separator support or
new option-value syntax is introduced. Put the Quick operation and id before
its options as shown by the command's usage.

The previously delivered all-entrypoint discovery patch is superseded for these
files: it uses overlapping helper names and older strict baselines. Do not
apply it on top of this increment. Any remaining help/show work must be a fresh
small change against the current source, reusing the current output contract.

Classic/Advanced generated consumers are not enabled automatically. Installation,
public distribution, adaptive delegation and cross-stage execution are unchanged.
No merge, release or public source publication is authorized by this document.

## Validation

The exact output-contract/parser/projection functions and existing lazy-rendering
tests can be tested without external dependencies:

```sh
GO111MODULE=off go test -race -count=1 -v quick_execution_output.go quick_execution_response.go quick_execution_output_test.go quick_execution_lazy_test.go
GO111MODULE=off go vet quick_execution_output.go quick_execution_response.go quick_execution_output_test.go quick_execution_lazy_test.go
GO111MODULE=off go test -run '^$' -fuzz '^FuzzQuickOutputLiteralValues$' -fuzztime=3s -parallel=2 quick_execution_output.go quick_execution_response.go quick_execution_output_test.go
```

These tests check the exact supported denominator, producer-schema agreement,
full-context recovery, fresh collections, preservation of existing descriptors,
and flag/value boundaries. They do not execute the complete runtime service.
The package tests in `quick_execution_output_integration_test.go` exercise the
real `Run -> api pack` and `Run -> quick -> runExecution` paths in a complete
checkout, including read-only discovery and early invalid-input failure.

Required before rollout:

```sh
go test -count=1 -run 'TestQuick(Output|Scope|Queue|Lazy|Compact|Resume)' .
go test -count=1 ./...
go vet ./...
```

A helper pass is not a complete runtime, Work/SQLite, installed-profile, cloud
CI or real-agent pass. This increment supplies no measured production token,
latency or quality-retention percentage.
