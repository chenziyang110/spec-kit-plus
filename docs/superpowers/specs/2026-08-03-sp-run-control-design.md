# SP Run Control Design

## Status

This document is the implementation contract for replacing project-wide workflow
serialization with independently isolated Runs. It supersedes the retired
Feature Lane model. Human product acceptance remains an explicit user action.

## Goals

- A project may execute multiple modifying `sp-*` or `spx-*` workflows at once.
- The first modifying invocation may use the primary workspace only when no
  other modifying Run exists. Every overlapping invocation is isolated.
- A modifying Agent executes only under runtime-issued workspace, fence, and
  resource authority.
- Agent reports are input. Runtime-derived snapshots, Results, Candidates,
  Review receipts, acceptance receipts, and publish receipts are authoritative.
- No automated stage may silently merge into or overwrite a user workspace.

## Workflow identity

- `quick`, `debug`, and `fast` create a new Run for every invocation.
- `specify` creates one feature Run.
- `plan`, `tasks`, and `implement` resume that same feature Run.
- `review` operates on one frozen Candidate identity and digest.
- `accept` records a human decision for exactly that reviewed Candidate.
- Integration repair is itself a Run and produces a new Result.

## Runtime aggregates

### Run

Run is the durable lifecycle owner. Attempts are fenced leases under a Run;
manual interruption cannot leave a permanently authoritative `active` state.

### Snapshot

A pre-launch Snapshot freezes:

1. the target ref and base commit/tree;
2. an Ambient Overlay containing eligible staged, unstaged, and untracked
   context already present in the source workspace; and
3. an immutable input manifest digest.

Ambient content is stored in a local content-addressed object store outside the
normal Git object database. Ignored files and secret candidates are excluded.
Tracked and untracked provenance is retained. Snapshot capture must not modify
the source branch, index, files, or status.

### Workspace

A Workspace is materialized from the Snapshot in a runtime-owned worktree. Its
attestation binds the canonical root, Git common/admin directories, base
commit, overlay digest, writable roots, and generation. A modifying Attempt
cannot activate without a valid attestation.

### Attempt and resources

An Attempt has one owner epoch and monotonically increasing fence. Managed
launch uses literal argv, the attested workspace as cwd, a platform process
container, supervisor-owned heartbeat, and a scoped environment. Resource
claims serialize exclusive resources while allowing compatible shared claims.
At minimum the runtime allocates isolated temp, cache, log, service, database,
and port namespaces or explicitly blocks/serializes an unknown shared resource.

Adapters publish runtime-owned capability manifests. Modifying execution
requires enforced cwd, file workspace root, writable roots, process-tree
control, cancellation, and structured Result support. Advisory or prompt-only
capabilities may not claim safe modifying parallelism.

### Sealed Run Result

A Sealed Run Result is append-only and distinct from an Activity's Worker
Result. Runtime sealing derives the changed tree and paths, binds the Snapshot,
Attempt fence, workspace/resource attestations, validation evidence, worker
report digests, and eligibility, then writes a hidden Git ref using CAS.

Eligibility is one of:

- `ready`
- `blocked`
- `failed`
- `overlay_dependent`
- `requires_effect_approval`

Only `ready` Results enter an automatic Candidate build. Reopening a Run creates
a new Result revision and an explicit supersession edge; old Results never
mutate.

### Candidate Build and Candidate

A Candidate Build freezes a target OID and a dependency-closed Result set. It
applies Result deltas in deterministic topological order inside a hidden
integration workspace. The target branch and user workspace remain unchanged.

A successful build produces one immutable Candidate with:

- exact target ref and expected OID;
- ordered Result IDs and manifest digests;
- candidate tree and commit chain;
- manifest digest; and
- immutable hidden ref.

New Results cannot join an existing Candidate. Conflict repair produces an
Integration Result and a new Candidate. Target drift makes the build stale.

### Review, Accept, and Publish

Review launches and validates the exact Candidate, and all integrated evidence
is bound to its manifest/tree digest. Isolated evidence cannot satisfy an
integrated evidence requirement.

Accept is a human-authored receipt that names the same Candidate, Review digest,
evidence digest set, decision, and timestamp. Runtime success never implies
human acceptance.

Publish is the only operation allowed to update the delivery target. It uses
CAS from the Candidate's expected target OID to its reviewed/accepted commit.
Any target drift, stale Review, stale acceptance, dirty protected target
workspace, or digest mismatch blocks publication. User-workspace synchronization
is a separate guarded step and never overwrites local modifications.

## Default routing and isolation

The first modifying Run may be primary-workspace backed only if the runtime can
prove there is no other live modifying Run and the host can enforce the same
authority contract. When overlap exists, or when proof is unavailable, the Run
must use an isolated Workspace. Read-only operations do not consume the single
primary modifying slot.

Dependencies are explicit Run/Result edges. A dependent Run cannot start from a
base that omits a required Result. Inferred relationships are warnings and do
not change authoritative topology.

## Recovery and cleanup

- Every external mutation is journaled as prepared, executing, and a definite
  outcome or `outcome_unknown`.
- Stale supervisors fence Attempts and resource claims before recovery.
- Uncertain workspaces are quarantined, never silently deleted.
- `park` preserves resumable state; `resume` reattests or allocates a new
  generation.
- `cancel` fences first, then terminates the process tree and releases claims.
- GC removes only released, retention-expired artifacts with no unsealed data;
  unsafe or dirty workspaces remain quarantined.

## Completion gates

1. Run kernel: durable state, revision/fence, leases, idempotency, recovery.
2. Snapshot/Workspace: immutable Ambient Overlay and attested materialization.
3. Supervisor/Adapter: enforced launch, process tree, resources, host routing.
4. Result Seal: append-only runtime-derived Results and evidence binding.
5. Candidate: multi-Result dependency closure, build, conflict recovery.
6. Review/Accept/Publish: exact digest binding and human acceptance boundary.
7. Hard cut: every modifying Classic/Advanced workflow uses Run Control; old
   Lane code and compatibility behavior are absent.

The feature is complete only when five real modifying workflows can execute in
parallel, produce independently sealed Results, converge into one Candidate,
pass Candidate-bound Review, wait for explicit human acceptance, and publish by
CAS without changing unrelated user workspace state.
