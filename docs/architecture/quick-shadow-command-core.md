# Quick shadow command core

## Current boundary

The command core landed at 70d846c and is now connected to the optional
`quick.context-shadow` diagnostic capability. `Run` and `RunContext` select the
context-aware Quick router; API Handshake/List/Ensure/Show/Pack expose the same
read-only contract. Source registration is not a published binary release or
installed workflow adoption. No generated consumer has switched.

The older local cumulative v1/v2 and remaining-only registration archives are
superseded. Do not apply them over the current branch.

## Landed implementation

- `quick_context_shadow_command.go` owns exact selectors, bounded errors,
  shadow-only envelopes, cancellation checks, and complete encoded-output limits.
- `quick_context_shadow_cli.go` supplies the typed-owner adapter and
  contextual routing helper. The top-level router now calls the contextual helper.
- `quick_context_shadow_git.go` owns the existing Git identity query, now with
  caller cancellation, the five-second local deadline and a 16 KiB output bound.
- `quick_context_shadow.go` retains its old method signatures as background-context
  compatibility wrappers. Explicit `WithContext` variants propagate cancellation
  between bounded state reads and into each direct Git child.

The complete encoded response ceiling is 128 KiB, including envelope metadata and
runtime-bound argv. Encoding failures return no buffered partial JSON; overflow
returns a blocked response without the report. A late observed cancellation
replaces a success snapshot. A write racing with cancellation cannot be undone.

Git stdout is bounded during collection, not just checked afterward. Overflow
cancels the direct child. The writer does not embed bytes.Buffer, because a
promoted ReadFrom would let io.Copy bypass Write's budget. Child stderr is not
returned as a diagnostic. Parent deadlines remain authoritative when shorter than
the local timeout. Cmd.Run waits for the child/copying goroutines; this does not
claim cleanup of an arbitrary descendant process tree.

The byte reader preserves exact input bytes, rejects non-regular/oversized files,
checks path aliases with the existing secureProjectPath owner and checks context
before and after synchronous IO. Empty bytes remain a decoder error, not a file
read error. Synchronous filesystem calls cannot be force-interrupted by context;
repeated snapshots are not a transaction or hostile-writer sandbox.

## No new authority

The diagnostic neither mutates Quick state nor dispatches workers, starts work,
changes profiles, submits results, verifies a registered design or decides human
acceptance. `authorizes_execution`, `live_code_verified`, `acceptance_verified`
and `claim_ready` remain false. The full owner packet remains required; the
projection alone is not executable.

## Registration ownership and pending verification

`quick_context_shadow_discovery.go` owns the optional descriptor dispatcher and
augments the existing Quick help response without changing its legacy fields.
Both `runAPI` and `apiCapabilityDescriptor` call that dispatcher; non-shadow
capabilities delegate unchanged to `runAPIShow`. Compact packs retain the same
output contract rather than stripping non-authority fields. The small registry,
summary and query-timeout additions are source-owned, not prompt instructions.

This separation leaves `script_domains.go` and `agent_schema.go` unchanged;
ordinary Quick execution and existing descriptors keep their original owners.
The complete-checkout entrypoint suite checks mixed read/write capability packs,
legacy descriptor equivalence, real state reads and cancellation propagation.
Those complete integration gates, native OS checks and install/regression tests
must pass before release or consumer adoption. See the
[registration checkpoint](../workflow-quality/quick-shadow-registration-2026-09-17.md)
for the tests actually executed and [command guide](quick-shadow-cli.md) for use.
