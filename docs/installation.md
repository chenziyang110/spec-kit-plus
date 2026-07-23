# Installation Guide

## Prerequisites

- **Linux/macOS** (or Windows; PowerShell scripts now supported without WSL)
- AI coding agent: [Claude Code](https://www.anthropic.com/claude-code), [GitHub Copilot](https://code.visualstudio.com/), [Codebuddy CLI](https://www.codebuddy.ai/cli), [Gemini CLI](https://github.com/google-gemini/gemini-cli), [MiMo Code](https://mimo.xiaomi.com/mimocode/start), or [Pi Coding Agent](https://pi.dev)
- [uv](https://docs.astral.sh/uv/) for package management
- [Python 3.11+](https://www.python.org/downloads/)
- [Git](https://git-scm.com/downloads)

## Installation

### Install or Upgrade Spec Kit Plus

Spec Kit Plus is independently developed and distributed from this repository:

```powershell
python -m pip uninstall -y specify-cli
uv tool install specify-cli --force --from git+https://github.com/chenziyang110/spec-kit-plus.git
Get-Command specify -All
specify --help
```

The uninstall step is intentional. Windows, Conda, and previous pip installs can
leave an older `specify.exe` earlier on PATH, while development builds may still
report the same `.dev0` version string. Use `specify --help` to verify the
expected command surface and `specify check` to diagnose the active setup.

### Initialize a New Project

The easiest way to get started is to initialize a new project from Spec Kit Plus. Use
`--refresh` when you want uv to re-check the Git source instead of reusing a
cached build:

```bash
# Run from the current development head
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

### Install Unified Specify Runtime

Generated Agent workflows call the standalone `specify-runtime` binary for
fixed artifacts, typed workflow state, specification validation, and the
namespaced project cognition commands. Releases publish prebuilt binaries for
Windows, Linux, and macOS. `specify init` best-effort downloads the matching release asset into
`~/.specify/bin/` and pins that executable in the generated project's
`.specify/config.json`. If automatic download is unavailable, use the
installers below or set `SPECIFY_RUNTIME_BIN` to a custom binary path.
The same binary exposes `cognition semantic-audit-resume` for persisted semantic audit
state checks. The command compares a saved audit input/output pair against
workflow state; it does not authorize source changes or final claims, and does not grant P3/P4. Multiple `authorized_claims` require one `active_claim_type`, and failed,
blocked, skipped, or inconclusive verification results keep claim readiness
blocked with `verification_result_failed`, `verification_result_blocked`, or
`verification_result_inconclusive` until a newer matching passed rerun
supersedes them.
After the binary is pinned, empty projects initialized by `specify init` run
`specify-runtime cognition init-empty`. When there is no business code yet, that
bootstrap creates `.specify/project-cognition/status.json` and
`.specify/project-cognition/project-cognition.db` with
baseline kind `baseline_kind=greenfield_empty`; greenfield flows do not require
map-scan -> map-build solely because the graph has no paths. Projects with
existing code still use map-scan -> map-build when a full first brownfield
cognition baseline is needed for a first/missing/unusable baseline.

Workflow-owned mutation closeout is planner-first: source-changing `sp-*`
workflows run
`specify-runtime cognition closeout-plan --workflow "$ACTIVE_WORKFLOW" --format json`,
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
Closeout agents should use `known_unknowns` only for blockers that make the
cognition update unsafe to trust. If unrelated dirty or untracked working-tree
paths were excluded by explicit workflow-owned paths, record that as
`confidence_notes` or `boundary.initial_dirty_paths`, not as blocking
`known_unknowns`.

```bash
# Linux / macOS
curl -sSL https://raw.githubusercontent.com/chenziyang110/spec-kit-plus/main/tools/specify-runtime/install.sh | bash
```

```powershell
# Windows PowerShell
irm https://raw.githubusercontent.com/chenziyang110/spec-kit-plus/main/tools/specify-runtime/install.ps1 | iex
```

Go users can also install from source:

```bash
go install github.com/chenziyang110/spec-kit-plus/tools/specify-runtime@latest
```

Generated helper scripts prefer the project-pinned `runtime_launcher` in
`.specify/config.json`, then `SPECIFY_RUNTIME_BIN`, and finally
`specify-runtime` from PATH.

The same binary owns canonical Agent artifact access. Use `specify-runtime artifact catalog` to inspect deterministic scaffold kinds, `specify-runtime artifact scaffold --kind <plan-contract|quick-status> --path <project-relative-path> --vars <compact-json>` for create-only stable boilerplate, and the `artifact show` or `artifact prepare` -> `artifact submit` path for progressive reads and leased writes.

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

Use the canonical `ask` workflow for read-only evidence-backed project Q&A when
you need a direct answer from project files, templates, docs, state, or memory
before choosing an action workflow. Project cognition guides the search; live evidence
proves the answer. Same-topic follow-ups reuse the prior evidence set
when it still applies; project-slang terms are normalized into project vocabulary,
and complex answers separate proven facts from
evidence-derived inferences. `sp-ask` is independent from `sp-discussion`, creates
no ask state or handoff, makes no source edits, and does not run tests, builds,
package managers, or project CLI commands by default. There is no `specify ask`
Typer helper in v1.

When `specify` starts from a `discussion` contract, pass the handoff JSON path or discussion slug, or let it select the single eligible unconsumed ready contract. It validates ready status, consumer eligibility, the confirmed digest, target boundary, protected obligations, and source-contract integrity before feature creation, then derives the feature description from `handoff_goal`. `spec-contract.json` preserves semantic delta, stable evidence refs, and capability operations so upstream signals cannot silently disappear before planning.

Command-surface minimization must not delete capability. If upstream discussion
or specification text includes a new/create/scaffold/authoring operation,
downstream planning and task generation must preserve it through an explicit
public command, TUI route, core API, private helper, or user-confirmed deferral
carrying confirmation source, exact excluded behavior, residual risk, reopen or
stop condition, and downstream artifact.
Manual copy instructions and template-only docs can support that operation, but
they do not replace it unless the user chose that narrower entry point.

Before planning, `specify` performs deterministic self-review. A confirmed
discussion contract does not require another user review unless compilation
produces a non-empty user-owned semantic delta.

Use the canonical `prd-scan -> prd-build` workflow when an existing repository
needs a repository-first current-state PRD reconstruction archive. It is the
heavy reconstruction PRD lane: substantive `prd-scan` runs are
subagent-mandatory, critical claims target `L4 Reconstruction-Ready`,
`config-contracts.json` is part of the scan contract surface, and `prd-build`
compiles from the scan package without a second repository scan. It remains a
peer workflow path to `specify` and does not automatically hand off to `plan`.
`prd` remains a deprecated compatibility entrypoint only.

Use `discussion` for rough ideas that need product/technical shaping before formal specification or bounded quick execution. It persists meaning at semantic checkpoints, keeps human replies adaptive, and writes one canonical Agent-only `handoff-to-specify.json` only after explicit request, boundary lock, self-review, and user confirmation. `sp-specify` and `sp-quick` validate that JSON directly; no Markdown companion, reviewer guide, quick-specific handoff, or duplicated confirmation is required.

Continue by default, do not ask for continuation, and ask only when user judgment is genuinely required and no safe default exists.

Current discussion state is Agent-native: `discussion-state.json` is canonical,
`discussion-state.md` is a derived compatibility view, and
`discussion-log.jsonl` records semantic checkpoints. The Context Boundary Gate
locks the target project root before technical claims. Human replies stay
natural; the handoff is JSON-only and approval/consumption bind to
`review_digest`. Draft validation runs before approval; `specify discussion
confirm-handoff <slug> --digest <review-digest>` records exact confirmation,
and only then may `mark-ready` expose the downstream workflow.

The discussion output is one canonical Agent-only JSON contract shared by eligible consumers.

Across the full pipeline, the canonical Agent authorities are `handoff-to-specify.json`, `spec-contract.json`, `plan-contract.json`, `task-index.json`, per-task lifecycle records, and post-closeout `human-acceptance.json`. Conditional artifacts are generated only when their trigger is present; delegated packets are compiled just in time. `sp-accept` / `spx-accept` assumes the human returns without chat context, restores the product story, and guides one observable acceptance step at a time before recording the explicit human verdict.

When `sp-specify` consumes the contract, it writes `spec-contract.json` and preserves the decision digest by reference. `sp-quick` reuses the confirmed digest when its own semantic delta is empty.

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
>
> **Windows note:** Offline scaffolding requires PowerShell 7+ (`pwsh`), not Windows PowerShell 5.x (`powershell.exe`). Install it from the [official PowerShell page](https://aka.ms/powershell).

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
