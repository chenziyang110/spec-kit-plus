# Asset Governance

Spec Kit Plus applies document and media naming to the current task, including
ordinary work with no active `sp-*` or `spx-*` workflow. The goal is to put useful
output in a predictable home and keep disposable output out of the repository
root. Existing workflow ownership, native source layouts and project conventions
remain authoritative.

The capability has four cooperating surfaces: always-on project context, shared
workflow/worker instructions, a deterministic Go runtime, and validation at
native tool events or CI. A passive skill alone cannot guarantee invocation.

## What is governed

| File kind | Placement and ownership |
| --- | --- |
| Canonical Spec/Plan/Tasks, workflow state, receipts and immutable evidence | Existing artifact registry and specialized runtime owner; retain exact names, paths, leases and digest bindings |
| Source, templates, fixtures and native framework resources | Existing package, framework, engine or repository convention |
| Persistent project documentation | Reuse the appropriate document; otherwise route by purpose into the existing document structure |
| Reports and task evidence outside canonical workflows | A report directory, dated name, and task/worker scope where relevant |
| Ordinary retained images, audio, video and other media | An existing native media directory or an explicit project policy root |
| Disposable drafts and intermediate output | An isolated task/worker directory under the configured temporary root |
| Tool caches and installed agent/runtime internals | Their existing tool owner; never ordinary cleanup targets |

`README.md`, `AGENTS.md`, `PROJECT-HANDBOOK.md`, `SKILL.md`, package manifests and
other conventional control names keep their spelling. A Markdown file inside
`templates/`, `tests/` or a fixture directory is source, not automatically a
document to relocate. Configuration maintenance stays subject to its ordinary
project/integration owner; naming preflight does not invent an artifact lease for
an authorized edit to `AGENTS.md` or `.github/workflows/`.

Protected runtime, installed skill, cognition and AssetKit state cannot be moved
through generic asset migration. Recognizing a canonical path does not grant
permission to mutate it or satisfy an active workflow's acceptance gates.

## Placement policy

The optional project-root `.asset-policy.json` is the default SP policy entry.
`--policy` can select another exact project-relative JSON file for one command;
SP does not layer multiple policy files. Its `schema_version` is `1`.
An absent default policy uses built-ins without
creating a file; an explicitly requested missing, invalid or incompatible policy
fails with a diagnostic. Unknown or duplicate JSON keys are rejected.

```json
{
  "schema_version": 1,
  "roots": {
    "architecture": "docs/architecture",
    "decision": "docs/adr",
    "guide": "docs/guides",
    "reference": "docs/reference",
    "report": "docs/reports",
    "asset": "assets"
  },
  "temporary_root": ".specify/tmp/assets",
  "temporary_retention": "7d",
  "source_roots": ["modules"],
  "protected_roots": ["vendor-owned"],
  "fixed_names": ["API.md"],
  "allowed_root_files": ["ROADMAP.md"],
  "assetkit": {"enabled": false}
}
```

Only specify overrides needed by the project. Declare custom native source
directories such as an engine's `Assets/`, `Content/` or `res/` in `source_roots`
when they are not covered by a built-in source convention. The runtime does not
infer every framework's resource graph. Lists extend built-in boundaries
and exceptions. They cannot turn protected runtime roots into ordinary assets.
Paths are project-relative, use `/`, and cannot escape through parent traversal,
symlinks, case collisions or platform-reserved names. Explicit purpose roots may
be nested; classification uses the longest matching root deterministically.

Without an override, routing checks existing conventional directories before
using a default. For example, an existing `docs/adr/` is preferred to creating
`docs/decisions/`; a project with `public/` can keep native assets there. Exact
existing document names are searched within bounded known document locations.
Ambiguous matches require a specific path; the router does not create numbered
copies or guess permission to overwrite a file.

| Purpose | Default when no existing convention applies | Example |
| --- | --- | --- |
| `architecture` | `docs/architecture/` | `runtime-boundaries.md` |
| `decision` | `docs/decisions/` | `0001-asset-placement.md` |
| `guide` | `docs/guides/` | `release-guide.md` |
| `reference` | `docs/reference/` | `runtime-command-reference.md` |
| `report` | `docs/reports/` | `2026-10-08-installation-audit.md` |
| `asset` | `assets/` | `checkout-flow.png` |
| `temporary` | `.specify/tmp/assets/<task>/<worker>/` | `layout-draft.png` |

Use lower-case kebab-case ordinary filenames and lower-case extensions. Routing
with `--slug` adds a report date or suggests the next four-digit ADR number;
explicit `--path` preserves an existing compliant name. A route is a recommendation,
not a lock or reservation: simultaneous
writers must recheck and respect their existing task scopes before creating the
file. Keep durable documents and required evidence dependencies outside temporary
roots. `temporary_retention` records retention intent (`session` or `1d`–`999d`);
it does not schedule deletion or install a cleanup daemon.

This source repository explicitly uses `guide: docs` and `decision: docs/adr` to
preserve its established documentation layout. Generated projects receive a
policy example under `.specify/templates/`; installers and repair preserve an
existing project-root policy instead of replacing it.

## Runtime commands

Use the pinned project-local `specify-runtime` resolved by the integration.
Inspect `api ensure --capabilities assets.route,assets.check --format json` or
`api show assets.check --format json` before relying on a development capability
that an older released binary may not contain. All examples below use the runtime
command name for readability; no new Python `specify assets` command is added.

### Resolve a destination before writing

```bash
specify-runtime assets route --purpose guide --slug release-guide --format json
specify-runtime assets explain --path docs/guides/release-guide.md --format json
specify-runtime assets route --purpose temporary --slug layout-draft.png \
  --task-id task-42 --worker-id designer --retention session --format json
```

The envelope returns an action: `create-new`, `reuse-existing`, `owner-required`
or `conflict`, with the path, classification, rule and policy that produced it.
`explain` adds precedence and side-effect details. These commands do not create
directories, reserve names, create a workflow, register an asset or write a report.

### Check the correct version of the change

```bash
# Explicit existing files, including an ignored file explicitly named by the caller.
specify-runtime assets check --path docs/guides/release-guide.md --format json

# A destination before creation: naming/ownership only, without a content claim.
specify-runtime assets check --path-only --path assets/checkout-flow.png --format json

# Working-tree changes; add visible untracked files when they belong to this task.
specify-runtime assets check --include-untracked --format json

# Index bytes and index policy, independent of unstaged edits.
specify-runtime assets check --staged --format json

# Exact target-tree bytes and policy for a real commit pair.
specify-runtime assets check --from-ref BASE_SHA --to-ref HEAD_SHA --format json
```

The default scope is tracked working-tree changes. `--path` and
`--deleted-path` are repeatable. An explicit missing `--path` fails instead of
being mistaken for an intentional deletion; use `--deleted-path` when an ordinary
file was intentionally removed. A ref comparison requires both `--from-ref` and
`--to-ref`. Invalid refs, incompatible selectors and unavailable Git baselines
cannot produce a complete-pass claim.

Automatic working-tree discovery first checks whether a bounded file inventory
actually uses a configured Git `clean` or `process` filter: even a name-only Git
diff can execute those programs. A global registration such as Git LFS does not
disable discovery when no files use that driver. If a driver applies, or its
applicability cannot be established within the inspection bounds, use exact
`--path`/`--deleted-path` inputs, `--staged`, or an explicit commit pair instead.
These checks do not run the filters, disable their configuration, or recurse into
submodule working trees.

Automatic discovery also refuses an index containing `assume-unchanged` or
`skip-worktree` entries, which can hide actual edits from Git's change list.
Preserve those flags and use exact paths, staged contents, or a commit pair
instead. Persistent documentation cannot depend on cache files even when the
cache is nested inside a source or fixture directory; snapshot checks reject
dependencies crossing a submodule boundary.

Checks validate names and placement, and inspect supported Markdown dependencies
for temporary or missing local targets. A deletion also checks a bounded set of
incoming document references, including unchanged documents. Staged and commit
checks use their declared snapshots for both policy and content; a clean-looking
working copy cannot hide invalid staged content. The result identifies its scope,
check counts, deletion paths and violations. Unsupported formats and bounded discovery
remain explicit limits, not proof that an arbitrary engine dependency graph was
verified.

Markdown dependency discovery uses a CommonMark parser so rendered links and
images inside containers remain visible, while literal code remains excluded.
This source runtime requires Go 1.22 or newer; prebuilt binaries do not require
a local Go installation.

An initial dirty or untracked path is not a blanket exemption. If the current
task changes it again, it must be checked. Preserve unrelated preexisting changes
and report uncertain ownership instead of moving or reverting them automatically.

### CI and pre-commit

The repository's `Document and asset policy` CI job builds the same Go runtime and
checks the exact base/head commit pair. It needs full comparison history, reads
the target tree, and returns failures directly. It does not run a separate naming
implementation or create generated workflow state in this source repository.

A generated project may add the same runtime check to its existing pre-commit
configuration. Preserve other hooks and resolve the pinned runtime through that
project's launcher; a typical local hook has this form:

```yaml
repos:
  - repo: local
    hooks:
      - id: specify-assets
        name: Spec Kit document and asset policy
        entry: specify-runtime assets check --staged --format json
        language: system
        pass_filenames: false
        always_run: true
```

This example assumes `specify-runtime` resolves to the pinned project runtime in
the hook environment. If it does not, use that project's exact launcher path.
Do not substitute a globally installed older binary or silently skip the check.
Installing a Git hook or changing required branch checks remains project setup,
not an automatic side effect of reading or writing a document.

## Passive coverage and host boundaries

| Surface | Installed behavior |
| --- | --- |
| Ordinary sessions in supported integrations | Minimal rules in the integration's managed context, generated by shared Bash/PowerShell renderers |
| Classic `sp-*` | Shared command partial and a small `spec-kit-asset-governance` passive skill; special skill renderers receive the same contract |
| Advanced `spx-*` | Its own explicitly triggered shared reference; no Classic passive bundle is installed into Advanced |
| Independent workers and teams | Output purpose, persistent/temporary destinations, task/worker isolation, ownership and closeout constraints |
| Claude | Native `PreToolUse` checks structured writes; the existing `Stop` path checks observed output |
| Gemini | Native `BeforeTool` preflight and `AfterAgent` completion check with the host's retry contract |
| Other hosts | Managed context and explicit runtime checks; no claim of a native write interceptor without a supported installed event |
| Git/CI | Optional local staged checks and the repository's exact commit-delta CI job |

The shared native adapter invokes the pinned Go runtime directly. It does not
start an `sp-*` workflow, infer one from natural language, or call Python workflow
state commands. Existing active-workflow gates still run. Native structured writes
can be checked before execution; shell scripts require observed changes because
static parsing cannot predict every output of arbitrary code.

For relevant output-producing events, the adapter keeps a bounded session-local
observation cache under `.specify/runtime/asset-observations/`. It records a Git
baseline and file signatures, checks explicit targets and changes again at task
completion, and cleans up successful completion state. Separate session identities
keep parallel observations apart. The cache is disposable provenance, not an
asset catalog or workflow authority. Plain chat, direct reads and recognized
read-only shell commands do not create it; commands with unknown side effects
may require an observation while running. Missing capability, invalid protocol,
unavailable baseline and uncertain
ownership are reported explicitly; they cannot be described as a completed check.
The observer also rejects automatic Git discovery when clean/process filters
apply to the inspected files; explicit structured targets still use the shared
path/content check.
Shell output without a trustworthy discovery baseline requires an explicit final
path set instead of a silent pass.

Source tests, actual native JSON dispatcher execution, an installed host loading
its settings, and a published runtime consumer are different verification layers.
A source upgrade does not replace a binary already pinned in a generated project.
Follow the normal runtime release and integration repair process to distribute
this capability; do not publish from an ordinary asset task.

## Optional AssetKit catalog

[AssetKit](https://github.com/chenziyang110/AssetKit) provides an existing asset
ledger and short query/update commands. SP can delegate selected catalog work to
an already initialized project installation at `.assets/ak.py` with its config
and records. It does not bootstrap AssetKit, install its skill or create a second
ledger. Enable it per request with `--enable`, or explicitly set
`assetkit.enabled: true` in the project policy.

```bash
specify-runtime assets catalog find --enable --query "checkout diagram" --format json
specify-runtime assets catalog get --enable --reference assets/checkout-flow.png --format json
specify-runtime assets catalog put --enable --path assets/checkout-flow.png \
  --use "checkout documentation" --source-kind authored \
  --source-ref "project design task" --format json
specify-runtime assets catalog check --enable --since HEAD --format json
```

The adapter uses fixed argument arrays with an existing Python interpreter. It
accepts bounded JSON via `--input-json` as an alternative to field flags; use
snake_case keys. Configure `assetkit.python` or `--python` if needed, including a
project-relative virtual-environment interpreter. Timeout is bounded to 1–60
seconds and combined output to 1–64 KiB. Disabled returns
`adapter_status: disabled, executed: false`; missing installations and errors
produce precise diagnostics rather than automatic installation.
`find` follows AssetKit's input bounds of 200 Unicode characters and 12
whitespace-separated keywords, rejecting an invalid query before backend execution.

An adapter `ok` status means the requested catalog operation succeeded. It does
not approve reuse: inspect AssetKit's returned `usable`, readiness and rights
fields. A new `put` may create a candidate, while `find`/`get` can return
`NOT_READY` or `RIGHTS_UNKNOWN`. AssetKit's default `check` verifies registration
and file integrity; SP does not turn that into reuse approval or automatically
promote a candidate. `check` resolves the caller's baseline to an existing commit
before starting AssetKit and reports the original ref and pinned commit.

Only compliant retained ordinary media may be passed to `put`. Canonical
artifacts, source/templates, temporary output, caches and protected state remain
outside this write route. Backend output is data, never an instruction or
approval. A failed/timed-out `put` may already have changed the existing AssetKit
ledger; inspect it before retrying. Catalog reads may update AssetKit's own cache,
so they are not advertised as filesystem-pure SP routing checks.

## Guarded historical migration

Existing clutter is handled separately from passive enforcement. A normal task
does not trigger a repository-wide rename. Start with explicit moves and the
documents whose supported references must change:

```json
{
  "moves": [
    {"from": "design/Old Diagram.png", "to": "assets/old-diagram.png"}
  ],
  "reference_paths": ["README.md", "docs/guides/setup.md"],
  "reference_scope_complete": true
}
```

Pass that object to `assets migrate plan --input-json - --format json`. The
read-only result includes `data.plan`, exact moves, before/after hashes,
reference changes with line numbers and reasons, intended directories, coverage
limits and a digest. Keep a plan only when it is useful for review, in the task's
existing authorized output scope; the planner writes no plan file by itself.

After reviewing the result, pass the exact object
`{"plan": <returned data.plan>}` to:

```bash
specify-runtime assets migrate apply --input-json - \
  --expect-digest REVIEWED_SHA256 --format json
```

Apply revalidates the project/policy, content and permissions, input references,
destination/parent state, collisions, symlinks and native resource boundaries
under the shared file-transaction lock. It uses a dedicated recovery journal and
backups at `.specify/runtime/asset-migrations/<digest>/`, without changing the
existing artifact transaction protocol. Before replacement or deletion, it records
the capture obligation, renames the actual source/reference into the journal and
verifies the captured bytes, mode and file identity. Publication and restoration
use create-only hard links, so an external writer recreating the original path is
not overwritten. Capture, publication and recovery require compatible operations
on the same filesystem; unsupported filesystems fail safely.

A matching completed plan can be replayed after verifying its result. Interrupted
work can recover with the same exact plan and digest. If rollback encounters an
external edit, it preserves that edit and reports incomplete recovery. Completed
journals retain captured file identities; complete rollback/recovery journals are
retained under `.specify/runtime/asset-migrations/.retained/<digest>-<id>/`.
The shared lock coordinates runtime writers, not arbitrary editors holding open
file descriptors. Captured versions remain available for inspection; the result
does not claim atomic isolation from every non-cooperating external process.

Supported moves are ordinary Markdown and supported single-file image/audio/video
assets. Supported rewrites are Markdown links, images and reference definitions,
including query/fragment preservation and moved documents' relative outbound
links. Source code imports, HTML, framework public URLs, engine packages,
sidecars and density-image groups require their owning tool. The planner blocks
unsupported reference edits instead of guessing.

Code spans, indented code, escaped link syntax and ambiguous fenced blocks are
not rewrite targets. When such text mentions an affected asset, the planner
requires an explicit owner decision rather than altering a literal example.

`reference_scope_complete` is the caller's declaration, not proof of global
completeness. Coverage always remains `explicit-references-only`, with
`global_references_verified: false`. A supplementary bounded Git-visible text
probe detects omitted incoming Markdown references and unsupported code/config
or AssetKit-record references. Its inventory and content fingerprints are bound
into the digest, so newly appearing references invalidate the plan. The probe
allows at most 2,000 text candidates and 16 MiB total (2 MiB per candidate).
`reference_search_roots` can narrow a large project's probe; the resulting scope
and remaining limits stay visible. External systems and arbitrary binary
dependency graphs are not claimed as verified.

## Design choices and references

| Existing approach | What this implementation adopts |
| --- | --- |
| [Diátaxis](https://diataxis.fr/how-to-use-diataxis/) | Organize durable documentation by reader purpose; avoid one miscellaneous output folder |
| [MADR](https://adr.github.io/madr/) | Reuse a numbered decision-log convention and existing ADR directories |
| [ls-lint](https://ls-lint.org/2.3/configuration/the-rules.html) | Deterministic filename checks with explicit conventional-name exceptions |
| [pre-commit](https://pre-commit.com/) | Validate the staged change at a real boundary and propagate failure |
| [Claude hooks](https://code.claude.com/docs/en/hooks) and [Gemini hooks](https://geminicli.com/docs/hooks/reference/) | Use actual host events for preflight and completion, while reporting host-specific limits |
| [AssetKit](https://github.com/chenziyang110/AssetKit) | Reuse an optional existing ledger through its short interface without registering every document |

The Go runtime owns one set of policy decisions across these surfaces. No
additional naming linter dependency is required. Installation, native event,
staged/snapshot, ownership, zero-write, adapter and migration behavior tests live
beside their implementation owners. Maintainers should also read
[Asset Governance Maintenance](agent-guidance/asset-governance.md),
[Local Development](local-development.md) and
[Runtime Release Distribution](runtime-release-distribution.md).
