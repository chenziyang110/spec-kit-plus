# Runtime Context Compiler

## Purpose and current boundary

Compile a task-specific view while keeping workflow state, permissions and
acceptance owned by the existing runtime. The read-only Quick shadow adapter
has an explicit diagnostic CLI; it is not an installed workflow consumer.
See [Quick shadow command](quick-shadow-cli.md) for invocation and limits.

The model reasons about intent and implementation. Deterministic assembly retains
exact task, scope, state, source, artifact, restriction and acceptance bindings.
The packet is never a new source of truth or a permission grant.

## Implemented API

`StateResolver` and `ArtifactResolver` preserve explicit owner-selected inputs.
`Resolver.Resolve` preserves scope as well as all supplied constraints.
`ResolvedContext.ToCompileRequest().ToCompilerInput()` preserves task/workflow
identity, artifact paths AND reasons/digests, forbidden actions and state identity.
Slices are copied so later caller mutation cannot change a compiled packet.

`Compiler.Compile` is the backward-compatible, unbound inspection API.
`Compiler.CompileBound` validates a complete request and returns a v2 packet.
`Packet.VerifyAgainst` compares packet integrity with a fresh owner-resolved
request. Missing bindings, changed obligations, tampering, duplicate artifacts,
invalid portable paths and output-budget overflow fail with explicit errors.

## Required inputs for bound compilation

| Input | Meaning |
| --- | --- |
| Task ID and workflow | Exact selected task and owning workflow |
| Goal, scope and acceptance | Current contract, never inferred from filenames |
| State reference and SHA-256 | Exact state bytes resolved by the owning runtime |
| Source revision | Exact Git revision; live artifact digests also cover working-tree changes |
| Artifact path, reason and SHA-256 | Why each live input is selected and its content identity |
| Constraints, skills and forbidden actions | Preserved as supplied, not invented by the compiler |

The output schema is `schemas/context-packet.schema.json`. `bound: true` means
structural binding only; it does not prove live verification, permission,
acceptance, readiness or `claim_ready`. Hashes are integrity checks, not signatures.
The runtime owner must obtain facts through its trusted APIs and re-resolve them
before consumption. An Agent supplying matching strings is not verification.

`generated_at` is informational and excluded from the content digest. It is not
an authorization clock. The default output ceiling is 128 KiB; a caller may set
a smaller budget, never a larger ceiling. Overflow returns no partial packet.
No rule, approval or acceptance obligation is removed to meet a budget.

## Internal Quick shadow adapter

`quickService.contextShadow(workspace, itemID)` reads the selected project's
actual confirmation file and local Git identity. It uses `secureProjectPath`,
the existing Quick confirmation type, `computeQuickConfirmationDigest` and
`compileQuickWorkerPacket`. Input bytes are bounded before decoding; the legacy
unbounded loader is not used for this diagnostic. Tests compare the result with
the existing loader and packet builder on the same fixture.

`BuildQuickShadow` preserves the complete legacy owner packet, including its
UI/design bindings, exclusions, dependencies and result requirements. Its small
projection is NOT a replacement contract. The raw confirmation digest, complete
owner packet, project/worktree identity and Git HEAD bind the report. Empty or
unprojectable file scopes fail this diagnostic without changing the legacy path.
A second owner snapshot must match; matching inputs do not need a second bound
compilation. `VerifyQuickShadow` requires fresh owner reads and checks all report
fields except the informational generation time. Neither function writes state,
retries a blocked operation, repairs data, claims work or changes executors.

Duplicate or undeclared item/status rows and blocked, unknown or empty selected
statuses are refused; absent rows keep the owner's pending default. Dependencies
must satisfy the legacy packet builder, and an accepted item is not restarted.
Global/selected dispatch blockers remain blockers. Git overrides are cleared for
the read-only identity command; linked worktrees remain separate, and a parent
repository or missing HEAD is never a substitute identity.

Both `authorizes_execution` and `live_code_verified` are false. Only the selected
confirmation bytes and owner packet are read: referenced source files, registered
design approvals, live UI and real acceptance evidence are NOT independently
verified here. In particular, unchanged Git HEAD does not prove an unchanged
working tree. Future consumers must resolve those exact artifacts through their
owners and preserve all existing permission, Review and human acceptance gates.
Repeated reads detect observable drift, not every ABA race; this is not a
transaction, filesystem security sandbox or hostile-writer isolation boundary.

## Exact state reads and ready successors

The Quick shadow decoder preserves dynamic numeric metadata as `json.Number`;
it does not round a source identifier or decimal before checking the existing
confirmation digest. Typed owner fields must use their exact JSON names: a
`Confirmation_State` alias cannot overwrite `confirmation_state`, and a nested
`Status` alias cannot clear a blocked status. The existing bounded JSON validator
still rejects exact duplicate keys, lossy Unicode and trailing input. Dynamic
metadata maps retain their own case-sensitive keys; unknown non-alias fields
retain the typed owner's compatibility behavior and remain bound by raw bytes.

The original item-accept owner marks unblocked successors `ready`. Diagnostic
admission therefore accepts `pending`, `ready` and `in_progress`, while retaining
its ambiguity/terminal/dispatch checks and the original packet builder's
confirmation and accepted-prerequisite gates. A `ready` label is not permission
to execute or evidence that dependencies passed. No source file or stored digest
is rewritten to make either check pass. See the
[state-read checkpoint](../workflow-quality/quick-shadow-state-read-2026-09-17.md)
for reproduced failures, executed tests and remaining full-runtime validation.

## Rollout still required

The adapter and optional `quick.context-shadow` diagnostic capability now exist.
Command help, API show and API pack share the same non-authority contract.
Installed Classic/Advanced consumers and their existing capability minimums remain
unchanged. Before enabling any consumer, run the complete runtime and install regressions
and verify live artifact/approval inputs on real projects. Test both profiles;
then measure actual Agent cost and accepted outcomes. A synthetic assembly
benchmark is not a production speedup or token-saving result. See the
[Quick shadow checkpoint](../workflow-quality/quick-shadow-checkpoint-2026-09-17.md).

## Wire decoding and distribution

Use `DecodeBound` for persisted or transported bytes, not plain `json.Unmarshal`.
It rejects duplicate decoded keys, unknown or wrongly cased properties, explicit
null fields/items, wrong types, malformed UTF-8, unpaired surrogate escapes,
trailing JSON, excessive nesting and inputs beyond the 128 KiB ceiling. Failed
reads return no partial packet. Exact canonical tags also apply inside artifacts.
Valid Chinese, emoji, surrogate pairs and escaped literal backslashes round-trip.

Compilation rejects invalid UTF-8 before hashing, preventing different invalid
byte strings from collapsing into the same replacement character. Verification
checks the actual serialized packet size, including informational timestamps,
and rejects inconsistent artifact-path projections even with a recomputed hash.
`DecodeBound` proves neither freshness nor authority: retain `VerifyAgainst`
with fresh owner-resolved inputs and every existing workflow gate.

The wheel force-includes the canonical schema under
`specify_cli/core_pack/schemas/context-packet.schema.json`. Distribution tests
run the actual context package at that declared layout and validate Go-produced
JSON with the canonical schema. They are not a full wheel/install or Quick
integration test. See the [earlier repair checkpoint](../workflow-quality/repair-status-2026-09-17.md)
for its historical validation; do not count those runs as repeated in this increment.
