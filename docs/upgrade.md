# Upgrade and Repair Guide

Upgrade the `specify` CLI first, then choose what the project needs. Run
`specify integration repair` to refresh managed assets and check the runtime
binding, `specify integration migrate-skills` to move an existing skill
catalog, or `specify init` to add or regenerate a workflow profile. Upgrading
the CLI leaves project files in place until you run a project command.

## Before You Start

From the project root:

```bash
git status --short
specify integration list
specify check
```

Commit or back up work you cannot recreate. Pay particular attention to:

- `.specify/memory/constitution.md`;
- customized generated commands, skills, templates, hooks, or context files;
- `.specify/features/**` workflow artifacts;
- local runtime or Project Cognition state that you intend to preserve.

Do not use a broad regeneration command before reviewing those paths.

## 1. Upgrade the CLI

### Reproducible tagged release

Use the same release tag on each machine. This example uses `v0.8.8`.

```bash
uv tool install specify-cli --force --from "git+https://github.com/chenziyang110/spec-kit-plus.git@v0.8.8"
specify version
```

Matching prebuilt `specify-runtime` binaries for Windows, Linux, and macOS
are published separately. [Runtime releases](https://github.com/chenziyang110/spec-kit-plus-releases/releases)

### Current development head

Use `@main` when you want to try the current development branch.

```bash
uv tool install specify-cli --force --from "git+https://github.com/chenziyang110/spec-kit-plus.git@main"
```

Development commits can share the same `.dev0` package version. Verify the
command surface as well as the version:

```bash
specify version
specify --help
specify check
```

On Windows, stale pip, Conda, or uv entrypoints may shadow the intended CLI:

```powershell
Get-Command specify -All
```

If the first result points to an obsolete pip or Conda installation, remove
that copy from the environment that owns it or fix PATH order. A pinned `uvx`
invocation can also run the intended CLI directly.

## 2. Repair an Initialized Project

The preferred post-upgrade sequence is:

```bash
specify check
specify integration repair
specify check
```

`specify integration repair` refreshes shared and runtime-managed generated
assets in place. It uses the project's recorded integration/profile metadata
and preserves user-edited workflow content when the managed file contract says
the file is user-owned.

Review the resulting diff before continuing:

```bash
git status --short
git diff -- .specify
```

Run `specify integration list` to find the active integration and the skills
path for a skills-based integration. The active integration and its recorded
profiles are in `.specify/integration.json`.

### Project launcher and runtime binding

Current generated projects record trusted launchers in `.specify/config.json`:

- `specify_launcher` records the trusted human bootstrap/upgrade source;
- `runtime_launcher` binds every agent-facing workflow helper to the relative
  project entrypoint `.specify/bin/specify-runtime` (`.exe` on Windows).

Run the project-local `specify-runtime` executable with `doctor --format json`
to diagnose its binding. If it reports `bootstrap_required` or the executable
is missing, repair from the project root with a trusted external CLI.

```bash
uvx --from "git+https://github.com/chenziyang110/spec-kit-plus.git@v0.8.8" specify integration repair
```

Use the project-local executable to verify the runtime version after repair.

```powershell
.\.specify\bin\specify-runtime.exe version --format json
```

On Linux or macOS, run `./.specify/bin/specify-runtime version --format json`.
`specify version` reports the Python CLI version. Check the runtime separately
when a workflow needs a particular capability.

Do not edit managed hook command strings by hand unless the diagnostic
explicitly says the file is user-owned.

### Recovering an interrupted cognition closeout

Upgrading the CLI alone does not replace a project's pinned binary. After
`specify integration repair`, check the project-local runtime's `version` and
`api handshake --format json`: it must advertise `cognition.closeout.inspect`
and `cognition.closeout.repair`. Install compatibility checks reject older
binaries without either capability, including otherwise clean cached or release
binaries. A shared `.dev0` package version is not proof of the installed runtime
revision or capabilities.

If a queued intent repeatedly blocks closeout with
`repair_update_or_replay_intent`, stop retrying unchanged inputs. Follow returned
`recovery_argv`, or run the project-local runtime with
`cognition closeout inspect --intent-id <blocked_intent_id> --format json`.
Without an ID, inspect lists compact pending cards. Inspection does not require
a blocked scope receipt; an old successful `cognition-closeout.json` cannot
identify the failed intent.

Inspect the exact scope, workflow, state, `input_digest`, verification problems,
and returned action. If inspect directly offers `replay_argv`, execute it
unchanged; that intent does not require repair or replacement fields.
Execute an applicable returned `repair_argv` unchanged.
A new repair uses
`cognition closeout repair --intent-id <ID> --expected-digest <input_digest>
--verification-json - --format json`. Write a complete JSON array of real
verification records to stdin: each has `command`, an exact `result`
(`passed`, `failed`, or `recorded`), and optional `artifact`. Run missing checks
or recover trustworthy evidence; never invent command names or passing results.
An empty input cannot create a repair. Only a previously journaled repair may
resume without resupplying evidence when the runtime permits it.

Repair is limited to defective verification on an uncommitted intent. It
archives the original and creates a digest-bound successor without changing
other payload semantics, scope, paths, or delta content. A returned
`closeout_status=intent_repaired` does not mean closeout passed. Use its
`replacement_intent_id`, `replacement_input_digest`, and `replay_argv`; exact
replay uses `cognition closeout replay --intent-id <ID> --expected-digest
<SHA256> --format json`. A supplied scope must match. The legacy
`--scope-dir` replay path remains available only for its matching blocked
receipt. Reinspect if the digest changed, then resume the original closeout
after the older intent replays and verify the original workflow's own receipt.

Do not hand-edit or delete intent JSON, fabricate receipts, bypass the queue,
or rebuild cognition merely to clear malformed verification. If no safe repair
or replay is offered, preserve the exact diagnostic, missing evidence, and
resume action. A real schema or baseline incompatibility follows its separately
reported recovery route below.

## 3. Regenerate or Add a Workflow Profile

Use a full init pass when you intentionally need to add an integration, add the
other workflow profile, or regenerate catalog surfaces that repair cannot
reconstruct:

Command shape:

```bash
uvx --from "git+https://github.com/chenziyang110/spec-kit-plus.git@v0.8.8" \
  specify init --here --force --ai <your-agent> --workflow-profile <classic|advanced>
```

Use `agy` as the agent key for Antigravity. For the full key list, run
`specify init --help`.

Review local changes first. This operation is broader than
`specify integration repair` and may refresh templates, scripts, context files,
and agent-native workflow surfaces.

Classic and Advanced installs are additive for skills-based integrations:

- Classic installs the full `sp-*` workflow and passive-skill surfaces.
- Advanced installs the independent `spx-*` catalog plus the unchanged Classic
  `sp-map-scan`, `sp-map-build`, and `sp-map-update` companions.
- Re-running init for the other profile should preserve both installed profile
  records and user-modified files.

Project feature work lives under `.specify/features/**`. Treat those artifacts,
source code, tests, and git history as user/project state; inspect the diff and
do not remove them as part of an upgrade.

### Migrate an Installed Skill Layout

`v0.8.8` defaults to `.agents/skills/` on new installs for integrations that
support it. Existing projects keep their recorded layout during upgrade and
repair. From the project root, check the active integration. If it supports
shared skills, migrate its managed catalog to the shared directory.

```bash
specify integration list
specify integration migrate-skills
specify integration list
```

For an integration with a separate native skills directory, pass
`--skills-layout native` to move the managed catalog there. Antigravity uses
`.agents/skills/` in either layout. If the project has several recorded
integrations, migration acts on the one marked current. Review local changes
before running `specify integration switch <key>`. By default, switching
removes unchanged files owned by the outgoing integration, preserves modified
files, and makes the selected integration active. Review the resulting diff
before migrating.

The command moves the profiles and supporting files tracked by the active
integration. It leaves independently managed skills in place and stops if a
tracked file has local edits or the destination conflicts with another file.
Review the reported paths before retrying. If migration reports an extension or
preset with registered workflow skills, remove that add-on, migrate, then
reinstall it so its skills register in the new location.

## Project Cognition Compatibility

`specify-runtime` Project Cognition schema v5 is current-only. It does not
migrate or silently replace schema v4 or older stores.

If greenfield initialization reports:

```text
unsupported_legacy_runtime
readiness=unsupported_runtime
recovery_action=run_map_scan_build
```

the binary is running, but an incompatible
`.specify/project-cognition/` store already exists. This is not evidence that a
new runtime release is required.

Recovery:

1. Run `specify-runtime cognition archive-incompatible-store --inspect --format json`
   to inspect the exact database and its SHA-256 without changing files.
2. Execute the returned hash-guarded `archive_argv`. Never move, remove,
   archive, or replace `.specify/project-cognition/` files directly.
3. For a truly empty project, rerun initialization so
   `cognition init-empty` can create `baseline_kind=greenfield_empty`.
4. For a project with business code, run `sp-map-scan` followed by
   `sp-map-build` with the current pinned runtime.
5. Run `specify check` again and keep live repository evidence—not the graph—as
   the source of truth.

## Common Diagnostics

| Symptom | Current action |
| --- | --- |
| Expected CLI command is missing | Check `specify --help`, then inspect duplicate executables with `Get-Command specify -All` on Windows. |
| `Unknown agent 'antigravity'` | Use the `agy` key. Run `specify init --help` for the full list. |
| Generated scripts or hooks are stale | Run `specify check`, `specify integration repair`, then `specify check` again. |
| Agent does not show refreshed workflows | Check the active integration and skills path with `specify integration list`, inspect the recorded profiles in `.specify/integration.json`, then reopen the project in the agent. |
| Advanced skills are absent | Confirm the integration is skills-based and rerun init with `--workflow-profile advanced`. |
| Runtime helper cannot start | Run project-local `specify-runtime doctor --format json`; if it reports `bootstrap_required`, use the trusted human bootstrap/upgrade flow to reprovision `.specify/bin/specify-runtime`. |
| Project Cognition reports `unsupported_legacy_runtime` | Use `cognition archive-incompatible-store --inspect`, execute its guarded `archive_argv`, and then use the empty-project or brownfield recovery above. |
| CLI upgrade appears unchanged | Compare both `specify version` and `specify --help`; `.dev0` alone cannot distinguish development commits. |

## No-Git Projects

`--no-git` skips repository initialization; it does not disable workflow state
or make destructive regeneration safer:

```bash
specify init --here --force --ai <agent> --no-git
```

Without git, create a manual backup before regeneration. If workflow resolution
cannot infer the active feature, provide the feature explicitly through the
generated command or the documented `SPECIFY_FEATURE` environment variable.

## Verification Checklist

After an upgrade or repair:

- `specify version` and `specify --help` describe the intended CLI;
- `specify check` has no unresolved launcher or compatibility errors;
- `.specify/integration.json` records the intended integration and workflow profiles;
- the `specify_launcher` and project-pinned `runtime_launcher` in `.specify/config.json` resolve;
- the agent displays the expected native `sp-*` and/or `spx-*` surfaces;
- existing `.specify/features/**` artifacts and user changes remain intact;
- `git diff` contains only reviewed changes.

For versioned binaries and checksums, see the
[public runtime releases](https://github.com/chenziyang110/spec-kit-plus-releases/releases).
