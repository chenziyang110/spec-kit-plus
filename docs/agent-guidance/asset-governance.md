# Asset Governance Maintenance

Read this reference before changing ordinary document and asset routing, naming,
retention, migration, catalog adapters, or their native integration guards.
These are source-repository maintenance instructions, not an instruction to enter
a generated workflow.

## Ownership and scope

Asset governance supports the current authorized task, including ordinary tasks
that do not invoke an `sp-*` or `spx-*` workflow. It must never select, load, enter,
or hand off into a workflow implicitly. Active workflow gates remain active.

Resolve registered workflow artifacts and protected runtime roots before ordinary
path rules. Recognition does not grant a mutation lease or approval. Preserve the
exact feature/change identity, specialized owner, canonical filename, immutable
approval evidence and digest bindings. Unknown paths inside protected roots do not
fall through into ordinary documentation or temporary output.

Ordinary source, templates, fixtures, project documentation and native assets
remain repository files within the current task's write scope. Do not widen the
workflow artifact prepare/submit registry to govern all docs or media.

The source repository must not create downstream feature state merely to maintain
this capability. Source rules and project policy belong in versioned source;
repo-local `.specify/` remains disposable generated state.

## Shared implementation

Keep path and naming rules in the shared Go runtime and one versioned policy
schema. Missing project policy uses deterministic built-in defaults without
creating a policy, catalog, report or workflow state. Preserve project overrides
on initialization, additive installation, upgrades and repair.

Routing and checking are read-only. A suggested new path is not a reservation.
Distinguish reuse, creation, owner-required and collision outcomes. Actual writes
use the caller's existing ownership and concurrency control; never resolve a
collision by silently adding numbered copies or overwriting another writer.

Check explicit paths even when Git ignores them. Working-tree, staged-index and
revision-pair checks read their declared versions. Initial dirty/untracked state
is provenance, not a blanket exemption for a path changed again by this task.
Invalid or unavailable baselines must not produce a complete-pass claim.

Keep persistent documents and required evidence dependencies outside temporary
roots. Preserve native consumer naming, fixed control filenames and generated
surfaces; extensions alone do not make source templates into catalog assets.

## Integration and installation

Ship minimal always-on behavior through both shared context renderers and each
integration's actual context file. Keep complete guidance reachable in fresh
ordinary sessions. Classic may install `spec-kit-asset-governance`; Advanced must
not install the Classic passive bundle and uses its own explicit reference plus
the same runtime. Pass scoped output constraints to independent workers.

Native guards must use the pinned project runtime and capability discovery. Keep
host event schemas, failure behavior and missing-capability limits explicit.
Structured file writes may be checked before execution. Shell outputs require
observed changes; do not claim a parser predicts every output of arbitrary code.
Any adapter checkpoint is bounded, task/session-local disposable observation
state, not workflow authority or an asset ledger. Ordinary chat, read-only tasks
and successful no-change checks leave no governance reports or residual state.

## Optional catalog and migration

AssetKit is an explicit optional adapter to an existing project installation.
Do not install or bootstrap it automatically, maintain a competing ledger, or
register every Markdown file. Canonical, temporary and internal state cannot be
sent through the ordinary catalog write path.

Migration starts with a read-only reviewable plan containing exact moves,
explicit reference scope, content preconditions and a digest. Applying that exact
plan validates all preconditions before mutation and uses guarded recovery.
Reject canonical/state paths, collisions, escaping or redirected paths and
unsupported reference rewriting. Explicit reference coverage never proves
arbitrary code references have been exhaustively discovered.

## Verification

Exercise ordinary tasks without workflow activation; Classic-only,
Advanced-only and additive installs; Bash/PowerShell context parity and custom
text preservation; relevant native events without active workflow state; shell
output discovery; staged/worktree divergence; preexisting dirty/untracked files
changed again; persistent-to-temporary references; concurrent route collisions;
read-only/no-change absence of side effects; optional adapter argv and failures;
and migration drift, rollback, replay and reference scope.

Run focused Go behavior tests and affected Python integration/packaging tests.
Distinguish source tests, generated installation, actual host loading, cloud CI
and runtime release distribution in completion claims.
