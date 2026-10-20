## Write-Scope Dispatch (Cross-Workflow)

These rules apply to every `sp-*` / `spx-*` workflow that dispatches subagents
or chooses between `leader-inline` / `leader-direct` and native workers.

### Shape selection

| Situation | Default `dispatch_shape` |
|-----------|--------------------------|
| Two or more independent ready lanes with **non-overlapping** write scopes | `parallel-subagents` |
| One ready lane, dependent lanes, or lanes that **share/overlap write scope** (same file, package, registry, generated consumer, or mutable shared state) | `one-subagent` (serial; resume the same worker or start a replacement with the next packet) |
| Dispatch or packetization fails | repair the packet, discover capabilities, join capacity-limited work, then resume or redispatch a safe serial lane; only after no safe authorized recovery remains use the workflow-specific blocked shape or explicitly permitted fallback |

### Hard distinctions

- **Write-scope conflict ≠ leader-inline authorization.** A runtime or policy
  rejection of a parallel wave for overlapping writes only forbids
  `parallel-subagents`. It does **not** mean the Leader should implement the
  lane. The correct default is serial `one-subagent` through the owning
  workflow's start/accept or join gates.
- **Cannot parallelize ≠ must self-write.** Prefer one serial native worker over
  unrecorded Leader implementation whenever the owning workflow is
  subagent-preferred, subagent-mandatory, or adaptive-standard with native
  subagents available.
- **Small or tightly coupled work** may still be Leader-owned only when the
  owning workflow explicitly permits `leader-direct` / `leader-inline` for that
  mode (for example adaptive light, debug small evidence chain, or implement
  leader-direct qualification). Size alone never converts a failed parallel
  plan into silent Leader implementation.
- **Dispatch failure is recovery work.** Preserve accepted results and pending
  joins while diagnosing or redispatching. Never fabricate independent
  acceptance or use a capability failure to enter another user-invoked workflow.

### Recording requirements

Before any Leader source edit that replaces a would-be subagent lane:

1. Record `attempted_shape` (usually `one-subagent` or `parallel-subagents`).
2. Record `chosen_shape` (`leader-inline`, `leader-direct`, or
   `subagent-blocked`).
3. Record a concrete reason (capability missing, unpacketizable, user-approved
   gated fallback, or workflow-allowed light mode)—not "same file" alone.
4. Prefer the workflow's state surface (`STATUS.md` `blocked_dispatch`,
   implement lifecycle, workflow-state, or session patch fields).

Unrecorded Leader implementation after a parallel write-conflict or after a
validated packet exists is a process defect.
