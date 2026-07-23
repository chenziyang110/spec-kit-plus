# Upgrade and Repair Guide

This guide covers three separate operations:

1. upgrade the `specify` CLI;
2. repair runtime-managed assets in an initialized project;
3. intentionally regenerate or add workflow profiles.

Keep them separate. A CLI upgrade does not automatically rewrite a generated
project, and ordinary project repair should not overwrite user-edited workflow
content.

## Before You Start

From the project root:

```bash
git status --short
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

Use a tag from
[Spec Kit Plus Releases](https://github.com/chenziyang110/spec-kit-plus/releases):

```bash
uv tool install specify-cli --force --from git+https://github.com/chenziyang110/spec-kit-plus.git@vX.Y.Z
```

Tagged releases publish matching prebuilt `specify-runtime` binaries for
Windows, Linux, and macOS.

### Current development head

Use the untagged repository only when you intentionally want the latest
development state:

```bash
uv tool install specify-cli --force --from git+https://github.com/chenziyang110/spec-kit-plus.git
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

If necessary, remove the obsolete installation before reinstalling:

```powershell
python -m pip uninstall -y specify-cli
uv tool uninstall specify-cli
uv tool install specify-cli --from git+https://github.com/chenziyang110/spec-kit-plus.git@vX.Y.Z
```

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

Also inspect the selected agent directory, such as `.codex/`, `.claude/`,
`.gemini/`, or the directory recorded in `.specify/config.json`.

### Project launcher and runtime binding

Current generated projects record trusted launchers in `.specify/config.json`:

- `specify_launcher` binds project helpers and native hooks to the intended
  Python CLI source;
- `runtime_launcher` binds workflow helpers to the project-pinned
  `specify-runtime` binary.

Generated helpers prefer `runtime_launcher`, then `SPECIFY_RUNTIME_BIN`, then a
`specify-runtime` executable on `PATH`. If `specify check` reports stale or
missing launchers, run repair from a trusted external CLI installation:

```bash
uvx --refresh --from git+https://github.com/chenziyang110/spec-kit-plus.git specify integration repair
```

Do not edit managed hook command strings by hand unless the diagnostic
explicitly says the file is user-owned.

## 3. Regenerate or Add a Workflow Profile

Use a full init pass when you intentionally need to add an integration, add the
other workflow profile, or regenerate catalog surfaces that repair cannot
reconstruct:

Command shape:

```bash
uvx --refresh --from git+https://github.com/chenziyang110/spec-kit-plus.git \
  specify init --here --force --ai <your-agent> --workflow-profile <classic|advanced>
```

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

1. Decide whether the existing Cognition state contains anything you need.
2. Archive `.specify/project-cognition/` outside the active path; remove it only
   after confirming it is disposable.
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
| Generated scripts or hooks are stale | Run `specify check`, `specify integration repair`, then `specify check` again. |
| Agent does not show refreshed workflows | Confirm the integration/profile in `.specify/config.json`, restart the agent/IDE, and inspect the generated agent directory. |
| Advanced skills are absent | Confirm the integration is skills-based and rerun init with `--workflow-profile advanced`. |
| Runtime helper cannot start | Check `runtime_launcher`, `SPECIFY_RUNTIME_BIN`, and `specify-runtime` on `PATH`, in that order. |
| Project Cognition reports `unsupported_legacy_runtime` | Archive the incompatible store and use the empty-project or brownfield recovery above. |
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
- `.specify/config.json` records the intended integration and workflow profile;
- project-pinned `specify_launcher` and `runtime_launcher` resolve;
- the agent displays the expected native `sp-*` and/or `spx-*` surfaces;
- existing `.specify/features/**` artifacts and user changes remain intact;
- `git diff` contains only reviewed changes.

For release-specific changes and binary assets, use
[Spec Kit Plus Releases](https://github.com/chenziyang110/spec-kit-plus/releases)
as the authoritative history.
