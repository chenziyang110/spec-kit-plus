# Runtime Context Compiler

## Purpose and current boundary

Compile a task-specific view while keeping workflow state, permissions and
acceptance owned by the existing runtime. This is a tested library foundation,
not yet a generated-workflow command or an installed Quick consumer.

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

## Rollout still required

First add a read-only Quick shadow adapter using its real state/artifact owners.
Compare it against existing task packets on identical snapshots before switching
any consumer. Preserve existing permission, result, Review and human acceptance
gates. Test installed Classic/Advanced behavior and the complete runtime before
claiming workflow integration or cost reduction. Other workflows follow only
after measured Quick evidence. No CLI command or production consumer is claimed
by this library change.

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
integration test. See the [repair checkpoint](../workflow-quality/repair-status-2026-09-17.md)
for measured validation and the still-open rollout boundary.
