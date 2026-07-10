Trigger: before planning synthesis or delegated planning lanes.

Purpose: validate one planning-ready spec contract and load only minimum sufficient planning context.

Preserved Contract: planning remains design-only, respects the active feature lane, and stops on invalid scope/boundary/evidence gates.

## Intake

1. Resolve the active feature directory/worktree and resume state.
2. Read `spec-contract.json` first and require `status: planning-ready` plus `transition.next_action: sp-plan` or equivalent canonical route.
3. Validate source revision, locked target boundary, zero hard blockers, acceptance coverage, and stable `MP-*`/`CA-###` refs.
4. Reuse the context capsule. Read only its required refs and any live paths whose stale condition is true.
5. Load constitution, project rules, and relevant learning detail only when they are not already represented by a current contract ref.
6. Read deep research, UI, data, API, or external evidence only when selected by required refs.

Do not revalidate the original discussion contract or rebuild specification decisions. If `semantic_delta` changes a user-owned decision, return to specify/clarify. If evidence contradicts feasibility, route to deep research or the owning phase.

## Phase Lock

Record design-only allowed writes, forbidden source/test implementation, canonical input/output refs, current action, blockers, and next route in sparse resume state. Do not copy the spec contract into workflow state.

Run phase-specific extension hooks when configured. Artifact-only planning does not dirty project cognition; source/runtime changes are not allowed here.
