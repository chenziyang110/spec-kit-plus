# Installation Guide

## Prerequisites

- **Linux/macOS** (or Windows; PowerShell scripts now supported without WSL)
- AI coding agent: [Claude Code](https://www.anthropic.com/claude-code), [GitHub Copilot](https://code.visualstudio.com/), [Codebuddy CLI](https://www.codebuddy.ai/cli), [Gemini CLI](https://github.com/google-gemini/gemini-cli), [MiMo Code](https://mimo.xiaomi.com/mimocode/start), or [Pi Coding Agent](https://pi.dev)
- [uv](https://docs.astral.sh/uv/) for package management
- [Python 3.11+](https://www.python.org/downloads/)
- [Git](https://git-scm.com/downloads)

## Installation

### Install or Upgrade This Fork

For Spec Kit Plus, install from this fork rather than the upstream Spec Kit
repository:

```powershell
python -m pip uninstall -y specify-cli
uv tool install specify-cli --force --from git+https://github.com/chenziyang110/spec-kit-plus.git
Get-Command specify -All
specify --help
```

The uninstall step is intentional. Windows, Conda, and previous pip installs can
leave an older `specify.exe` earlier on PATH, while development builds may still
report the same `0.5.1.dev0` version string. `specify --help` should show the
current command surface, including commands such as `testing`.

### Initialize a New Project

The easiest way to get started is to initialize a new project from this fork. Use
`--refresh` when you want uv to re-check the Git source instead of reusing a
cached build:

```bash
# Install from the latest fork commit
uvx --refresh --from git+https://github.com/chenziyang110/spec-kit-plus.git specify init <PROJECT_NAME>

# Or pin a specific tag or branch when you need reproducibility
uvx --from git+https://github.com/chenziyang110/spec-kit-plus.git@vX.Y.Z specify init <PROJECT_NAME>
```

Or initialize in the current directory:

```bash
uvx --refresh --from git+https://github.com/chenziyang110/spec-kit-plus.git specify init .
# or use the --here flag
uvx --refresh --from git+https://github.com/chenziyang110/spec-kit-plus.git specify init --here
```

### Specify AI Agent

You can proactively specify your AI agent during initialization:

```bash
uvx --refresh --from git+https://github.com/chenziyang110/spec-kit-plus.git specify init <project_name> --ai claude
uvx --refresh --from git+https://github.com/chenziyang110/spec-kit-plus.git specify init <project_name> --ai gemini
uvx --refresh --from git+https://github.com/chenziyang110/spec-kit-plus.git specify init <project_name> --ai copilot
uvx --refresh --from git+https://github.com/chenziyang110/spec-kit-plus.git specify init <project_name> --ai codebuddy
uvx --refresh --from git+https://github.com/chenziyang110/spec-kit-plus.git specify init <project_name> --ai mimo
uvx --refresh --from git+https://github.com/chenziyang110/spec-kit-plus.git specify init <project_name> --ai pi
```

### Specify Script Type (Shell vs PowerShell)

All automation scripts now have both Bash (`.sh`) and PowerShell (`.ps1`) variants.

Auto behavior:

- Windows default: `ps`
- Other OS default: `sh`
- Interactive mode: you'll be prompted unless you pass `--script`

Force a specific script type:

```bash
uvx --refresh --from git+https://github.com/chenziyang110/spec-kit-plus.git specify init <project_name> --script sh
uvx --refresh --from git+https://github.com/chenziyang110/spec-kit-plus.git specify init <project_name> --script ps
```

### Ignore Agent Tools Check

If you prefer to get the templates without checking for the right tools:

```bash
uvx --refresh --from git+https://github.com/chenziyang110/spec-kit-plus.git specify init <project_name> --ai claude --ignore-agent-tools
```

### Install Project Cognition Runtime

Generated project cognition workflows call the standalone `project-cognition`
binary directly. Releases publish prebuilt binaries for Windows, Linux, and
macOS. `specify init` best-effort downloads the matching release asset into
`~/.specify/bin/` and pins that executable in the generated project's
`.specify/config.json`. If automatic download is unavailable, use the
installers below or set `PROJECT_COGNITION_BIN` to a custom binary path.
After the binary is pinned, empty projects initialized by `specify init` run
`project-cognition init-empty`. When there is no business code yet, that
bootstrap creates `.specify/project-cognition/status.json` and
`.specify/project-cognition/project-cognition.db` with
baseline kind `baseline_kind=greenfield_empty`; greenfield flows do not require
map-scan -> map-build solely because the graph has no paths. Projects with
existing code still use map-scan -> map-build when a full first brownfield
cognition baseline is needed for a first/missing/unusable baseline.

Workflow-owned mutation closeout is planner-first: source-changing `sp-*`
workflows run
`project-cognition closeout-plan --workflow "$ACTIVE_WORKFLOW" --format json`,
passing `--delta-session "$DELTA_SESSION_ID"` when a delta session exists. The
planner returns `update_mode=delta_session` or `update_mode=payload_file`,
`required_agent_fields`, `unknown_path_dispositions`, display-only command
templates, and structured execution fields. Agents execute via `update_argv`
after writing a completed payload, or by completing
`delta_append_draft.argv_prefix` with agent-owned evidence placeholders before
running `update_argv`. Verified `adoptable` unknown paths can be recorded
without becoming blocking `known_unknowns`; only `blocking_known_unknown`
dispositions become payload or delta known unknowns. Clean closeout gates on
`result_state=ready` or `result_state=no_op`, not `status=ok`, `update_id`,
`last_update_id`, freshness, display-only command templates, or legacy
`recorded-only` output. `sp-map-update` remains manual/external maintenance and
artifact-only workflows do not write cognition unless they changed
source/runtime/template/config/test/generated-asset surfaces.

```bash
# Linux / macOS
curl -sSL https://raw.githubusercontent.com/chenziyang110/spec-kit-plus/main/tools/project-cognition/install.sh | bash
```

```powershell
# Windows PowerShell
irm https://raw.githubusercontent.com/chenziyang110/spec-kit-plus/main/tools/project-cognition/install.ps1 | iex
```

Go users can also install from source:

```bash
go install github.com/chenziyang110/spec-kit-plus/tools/project-cognition@latest
```

Generated helper scripts prefer `PROJECT_COGNITION_BIN` when set, then the
project-pinned `.specify/config.json` launcher when generated from `specify
init`, and otherwise call `project-cognition` from PATH.

## Verification

After initialization, you should see generated workflow commands or skills
available in your AI agent. Canonical workflow names such as `specify`, `plan`,
and `tasks` are integration-neutral, but the text you type depends on the
selected integration.

Invocation syntax depends on the integration:

| Integration surface | Specify | PRD | Plan | Tasks |
| --- | --- | --- | --- | --- |
| Codex skills | `$sp-specify` | `$sp-prd-scan -> $sp-prd-build` | `$sp-plan` | `$sp-tasks` |
| Kimi Code skills | `/skill:sp-specify` | `/skill:sp-prd-scan -> /skill:sp-prd-build` | `/skill:sp-plan` | `/skill:sp-tasks` |
| Claude skills | `/sp-specify` | `/sp-prd-scan -> /sp-prd-build` | `/sp-plan` | `/sp-tasks` |
| MiMo Code commands | `/sp.specify` | `/sp.prd-scan -> /sp.prd-build` | `/sp.plan` | `/sp.tasks` |
| Slash-dot command integrations | `/sp.specify` | `/sp.prd-scan -> /sp.prd-build` | `/sp.plan` | `/sp.tasks` |

`/sp-*` is not universal for skills-backed integrations. Use the invocation
syntax generated for your selected integration rather than copying Claude-style
examples into Codex or Kimi projects.

`sp-specify` is a collaborative reviewed specification flow. It explores
project context, asks one question at a time, compares two or three concrete
approaches when scope needs a choice, and forces semantic
traceability for ambiguous terms such as "capability", "real", "usable", or
"end-to-end".

When `specify` starts from a `discussion` handoff, it must read the named
discussion source files, at least `discussion-log.md`, `requirements.md`, and
`open-questions.md` when present, instead of trusting the handoff summary
alone. Invoke it with the handoff Markdown path, JSON path, or discussion slug,
or let it consume the single unconsumed `handoff-ready` discussion when exactly
one exists. It validates the handoff before feature creation, requires ready
planning status, user-confirmed quality gate status, zero hard unknowns, zero
open conflicts, and Markdown/JSON agreement on protected downstream facts, then
derives the feature description from `handoff_goal` instead of the raw path or
slug. The compatibility handoff JSON records `source_files_read` and
`source_signal_disposition`; `alignment.md` carries `Semantic Term Decisions`,
`Upstream Intent Disposition`, and `Out-Of-Scope Conflicts` so a capability-like
upstream signal cannot silently disappear before planning.

Command-surface minimization must not delete capability. If upstream discussion
or specification text includes a new/create/scaffold/authoring operation,
downstream planning and task generation must preserve it through an explicit
public command, TUI route, core API, private helper, or user-confirmed deferral.
Manual copy instructions and template-only docs can support that operation, but
they do not replace it unless the user chose that narrower entry point.

Before planning, `specify` performs artifact self-review and asks for user review
against the original wording so unconfirmed scope narrowing is reopened instead
of passed downstream.

Use the canonical `prd-scan -> prd-build` workflow when an existing repository
needs a repository-first current-state PRD reconstruction archive. It is the
heavy reconstruction PRD lane: substantive `prd-scan` runs are
subagent-mandatory, critical claims target `L4 Reconstruction-Ready`,
`config-contracts.json` is part of the scan contract surface, and `prd-build`
compiles from the scan package without a second repository scan. It remains a
peer workflow path to `specify` and does not automatically hand off to `plan`.
`prd` remains a deprecated compatibility entrypoint only.

Use the canonical `discussion` workflow for rough ideas that need resumable product/technical discussion before formal specification. `discussion` stores `.specify/discussions/<slug>/` artifacts, uses an Adaptive Question Pack with one required primary question and up to two optional same-topic follow-ups only for local low-risk topics, and runs the Context Boundary Gate before technical options or handoff generation. If the request crosses projects, references another codebase, names an external system, or depends on an existing module, lock the target project root, current project role, reference source, and evidence source before making project-specific claims. It acts as a senior product-engineering advisor: before project-specific technical advice it performs a Truth Pass, records verified project facts, open assumptions, checked evidence, and advice confidence, gives decision-ready judgment with evidence and risk, maintains a Discussion Compass, uses recommendation-first decision progression, keeps stable response formats, and proactively surfaces adjacent implications instead of forcing one-point-at-a-time replies. Recommendation-first is not questionless: when user judgment is needed, the response asks one explicit primary decision question with the recommended default and meaningful alternatives. When the user explicitly asks to hand off, `discussion` writes exactly one single unified handoff: `handoff-to-specify.md` plus `handoff-to-specify.json` only after self-review and user confirmation. Missing JSON is a hard integrity blocker for downstream intake. The Markdown handoff includes a `Handoff Reviewer Guide` with approval and change-request criteria for reviewers who do not know Spec Kit internals. Skills-based projects include `spec-kit-discussion-handoff-review`, which gives reviewers fixed verdicts and applies a ready summary quality check so the final handoff-ready closeout reads like a concise handoff card, not only updated paths and counters. Broad directions stay in `discussion` until they can be expressed as one handoff with a capability map, recommended sequence, dependencies, deferred scope, and reopen conditions. It does not automatically invoke `specify`; after `sp-specify` consumes the handoff, use `specify discussion mark-consumed <slug> --feature-dir <feature-dir>` to record handoff consumption and remove stale `handoff-ready` state from default auto-resume candidates.

When `sp-specify` consumes that handoff, it turns selected direction, rejected alternatives, accepted tradeoffs, experience commitments, review criteria, and must-not-dilute constraints into a `Discussion Decision Digest` carried through spec, alignment, context, and compatibility JSON.

Discussion sessions remain visible to resume while their status is `active`, `blocked`, or unconsumed `handoff-ready`. After a handoff has been consumed, `specify discussion mark-consumed <slug> --feature-dir <feature-dir>` writes `handoff_consumption_status: consumed`, `consumed_by_feature_dir`, `status: completed`, and `next_command: none`; then `specify discussion archive <slug>` can move it under `.specify/discussions/archive/`. If the user abandons the topic before consumption, use `specify discussion close <slug> --status abandoned` and then archive it.

The `.specify/scripts` directory will contain both `.sh` and `.ps1` scripts.

## Troubleshooting

### Enterprise / Air-Gapped Installation

If your environment blocks access to PyPI (you see 403 errors when running `uv tool install` or `pip install`), you can create a portable wheel bundle on a connected machine and transfer it to the air-gapped target.

**Step 1: Build the wheel on a connected machine (same OS and Python version as the target)**

```bash
# Clone the repository
git clone https://github.com/chenziyang110/spec-kit-plus.git
cd spec-kit-plus

# Build the wheel
pip install build
python -m build --wheel --outdir dist/

# Download the wheel and all its runtime dependencies
pip download -d dist/ dist/specify_cli-*.whl
```

> **Important:** `pip download` resolves platform-specific wheels (e.g., PyYAML includes native extensions). You must run this step on a machine with the **same OS and Python version** as the air-gapped target. If you need to support multiple platforms, repeat this step on each target OS (Linux, macOS, Windows) and Python version.

**Step 2: Transfer the `dist/` directory to the air-gapped machine**

Copy the entire `dist/` directory (which contains the `specify-cli` wheel and all dependency wheels) to the target machine via USB, network share, or other approved transfer method.

**Step 3: Install on the air-gapped machine**

```bash
pip install --no-index --find-links=./dist specify-cli
```

**Step 4: Initialize a project (no network required)**

```bash
# Initialize a project from bundled assets
specify init my-project --ai claude
```

`specify init` uses the templates, commands, and scripts bundled inside the
installed wheel, so the generated project matches the installed CLI version.

> **Note:** Python 3.11+ is required.

> **Windows note:** Offline scaffolding requires PowerShell 7+ (`pwsh`), not Windows PowerShell 5.x (`powershell.exe`). Install from https://aka.ms/powershell.

### Git Credential Manager on Linux

If you're having issues with Git authentication on Linux, you can install Git Credential Manager:

```bash
#!/usr/bin/env bash
set -e
echo "Downloading Git Credential Manager v2.6.1..."
wget https://github.com/git-ecosystem/git-credential-manager/releases/download/v2.6.1/gcm-linux_amd64.2.6.1.deb
echo "Installing Git Credential Manager..."
sudo dpkg -i gcm-linux_amd64.2.6.1.deb
echo "Configuring Git to use GCM..."
git config --global credential.helper manager
echo "Cleaning up..."
rm gcm-linux_amd64.2.6.1.deb
```
