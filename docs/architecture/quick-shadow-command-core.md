# Quick shadow command core: internal, not registered

## Current boundary

This increment lands the independently checked command core, Git subprocess
reader and cancellation-aware state-reader variants from the earlier local v2
patch. It does NOT apply that patch's top-level routing or capability-registration
hunks. `Run`, `RunContext`, `runQuick`, default capabilities, `api show`, `api pack`
and query-timeout classification remain unchanged in this commit.

Consequently `specify-runtime quick context-shadow` is NOT an available public
command at this checkpoint. The internal handler and descriptor helpers are
prepared for a separate registration increment; function names are not proof
that users or generated workflows can invoke them.

## Landed implementation

- `quick_context_shadow_command.go` owns exact selectors, bounded errors,
  shadow-only envelopes, cancellation checks, and complete encoded-output limits.
- `quick_context_shadow_cli.go` supplies the internal typed-owner adapter and
  contextual routing helper. They are not called by the top-level router yet.
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

## Registration and verification still pending

The remaining source registration touches script_domains.go, main.go,
agent_schema.go, capability_efficiency.go and command_timeout.go, plus the public
command guide and entrypoint tests from the local v2 package. Apply these as one
coherent follow-up, verify Help/Handshake/Show/Pack agreement, and execute the real
Run/RunContext tests in a complete checkout before any consumer switch.

Do not apply the older cumulative v2 package on top of this commit: it includes
already-landed paths and pins a different base. Preserve any user-owned edits.
The delivery checkpoint records precisely what was rerun and what remains open.
