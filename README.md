# Spec Kit Plus

**Spec-Driven Development workflows for local AI coding agents—from product intent to reviewed specifications, plans, tasks, implementation, integrated system review, and human acceptance.**

[![Latest release](https://img.shields.io/github/v/release/chenziyang110/spec-kit-plus?display_name=tag&sort=semver)](https://github.com/chenziyang110/spec-kit-plus/releases)
[![Test and lint](https://github.com/chenziyang110/spec-kit-plus/actions/workflows/test.yml/badge.svg)](https://github.com/chenziyang110/spec-kit-plus/actions/workflows/test.yml)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[Quick start](#quick-start) · [How it works](#how-it-works) · [Workflow profiles](#workflow-profiles) · [Integrations](#supported-integrations) · [Documentation](#documentation) · [Releases](https://github.com/chenziyang110/spec-kit-plus/releases)

Spec Kit Plus is an independently developed Spec-Driven Development toolkit for local AI coding agents. The `specify` CLI scaffolds a shared runtime and renders native commands or skills for the AI coding tool you select. The generated workflows then carry decisions through requirements, technical planning, execution, verification, and acceptance.

> [!IMPORTANT]
> Spec Kit Plus has its own templates, workflow profiles, runtimes, and release behavior. Install from `chenziyang110/spec-kit-plus` when you want the capabilities documented here. [GitHub Spec Kit](https://github.com/github/spec-kit) remains a separate project with its own canonical distribution.

## Why Spec Kit Plus

| Need | What this repository provides |
| --- | --- |
| Keep product intent intact | A reviewable artifact chain from `specify` through `plan`, `tasks`, `implement`, system `review`, and `accept`, with explicit repair and reopen paths. |
| Work in the agent you already use | One integration registry renders the same workflow concepts into skills, commands, prompts, hooks, and context files native to each supported tool. |
| Match prompts to the model | **Classic** keeps the full, explicit `sp-*` workflow; **Advanced** provides independent, prompt-optimized `spx-*` skills for skills-based integrations. |
| Navigate an existing codebase | Project Cognition narrows brownfield evidence reads and change-impact routes while requiring live repository verification before technical claims or edits. |
| Treat UI and acceptance as executable work | Change-scoped `.specify/design/changes/<UD-ID>/DESIGN.md`, feature `ui-brief.md`, task-local UI contracts, real-entrypoint evidence, and resumable human acceptance remain part of delivery rather than optional prose. |
| Extend without forking the runtime | Presets, extensions, a generic integration, project Learning, and optional team execution add capabilities around the shared CLI and artifact contracts. |

## Quick start

### Recommended setup

- [Python 3.11 or newer](https://www.python.org/downloads/)
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- [Git](https://git-scm.com/downloads) (recommended; `init --no-git` is available)
- the CLI or IDE for your chosen AI coding agent

### 1. Install the CLI

```bash
uv tool install specify-cli --from git+https://github.com/chenziyang110/spec-kit-plus.git
```

An untagged Git install follows the current development head. For a reproducible
CLI/runtime pair, append a tag from
[Releases](https://github.com/chenziyang110/spec-kit-plus/releases) to the Git
URL, for example `@vX.Y.Z`.

### 2. Initialize a project

```bash
specify init my-project --ai codex --workflow-profile classic
cd my-project
specify check
```

`specify init` creates the shared `.specify/` runtime and the native workflow catalog for the selected integration. `classic` is the non-interactive default; choose `advanced` when the integration supports skills and you want the independent `spx-*` catalog.

To scaffold once without installing the CLI:

```bash
uvx --refresh --from git+https://github.com/chenziyang110/spec-kit-plus.git specify init my-project --ai codex --workflow-profile classic
```

For an existing directory, run `specify init --here --force --ai <agent>` after reviewing local changes. Use `--ignore-agent-tools` when you only want the generated assets and do not want `init` to require the selected agent executable.

### 3. Start the workflow in your agent

The following is Codex skill syntax and is entered inside Codex, not in the shell:

```text
$sp-specify Build a searchable knowledge base with role-based access and an audit trail.
$sp-plan Use PostgreSQL, a REST API, and the existing frontend stack.
$sp-tasks
$sp-implement
$sp-review
$sp-accept
```

Other integrations use different punctuation. The `Start Here` panel printed by `specify init` shows the exact native commands for the selected agent.

## How it works

The normal pre-planning path is `specify -> plan`. Focused specification repair stays inside `specify`; feasibility research is a conditional branch, not mandatory ceremony.

```mermaid
flowchart LR
    D["discussion<br/>(optional shaping)"] -.-> S["specify<br/>requirements and acceptance"]
    D -. direct delivery .-> Q["quick<br/>resumable execution at any size"]
    S --> P["plan<br/>technical design"]
    S -. feasibility unproven .-> R["deep-research"]
    R --> P
    P --> T["tasks<br/>dependency-aware graph"]
    T --> I["implement<br/>execute task graph"]
    I --> V["review<br/>start, interact, repair"]
    V --> A["accept<br/>human product verdict"]
```

- Use `discussion` before formal specification or direct quick delivery when an idea still needs product or technical shaping.
- Use `quick` / `spx-quick` for resumable direct delivery when the requested outcome is already clear enough to implement without first creating a formal specification. Quick is not limited to small tasks: it may handle larger, multi-capability, architecture, migration, compatibility, rollout, or acceptance-heavy work through task-local planning, lanes or batches, consequence tracking, and validation.
- Use `specify` again when an existing specification needs a focused analysis or repair pass before planning.
- Use `deep-research` when requirements are clear but feasibility, external evidence, or an implementation chain still needs proof before planning. It binds the exact spec and capability set, leases bounded research tracks, validates source provenance and disposable-spike evidence, records leader accept/reject decisions with one retry, requires an independent audit, and publishes a digest-bound handoff that `plan` must verify. It does not rewrite requirements, choose the final architecture, or implement production code.
- Use `design` as an independent UI design input lane when a screen, component, interaction, responsive layout, TUI, or CLI presentation needs an approved visual contract. It feeds `specify` or `quick`; it is not a mandatory stage between Deep Research and planning.
- Use `sp-test-design` (Classic; rendered invocation `test-design`) / `spx-test-design` (Advanced) as an independent producer when a project, feature, formal Plan, Quick task, Tasks graph, or Review needs a frozen test universe, professional case catalog, test-data/material pack, explicit gaps, and bounded leader/subagent discovery. It does not require a completed Plan. It publishes a content-addressed package and typed pointer-only projections for selected read-only consumers. The default formal path still keeps `plan -> [optional test-design] -> tasks`, and completeness remains only `complete_against_frozen_scope`, never absolute.
- Review the seeded constitution and run `constitution` when the project needs explicit governance changes.
- Use `auto` to resume the safest next step from recorded workflow state.

### Workflow catalog

| Layer | Canonical workflows |
| --- | --- |
| Core workflow skills | `constitution`, `specify`, `plan`, `tasks`, `implement`, `review`, `accept` |
| Support skills | `auto`, `ask`, `discussion`, `deep-research` (`research` compatibility alias), `test-design`, `design`, `fast`, `quick`, `checklist`, `analyze`, `debug`, `explain`, `implement-teams`, `prd-scan`, `prd-build`, `prd` (deprecated compatibility entrypoint), `map-scan`, `map-build`, `map-update`, `taskstoissues` |
| Codex-only runtime | `sp-teams` for durable managed-team state and `team` for runtime operations inside the generated agent catalog |

The generated `ask` workflow is read-only, evidence-backed project Q&A. `prd-scan -> prd-build` reconstructs current product documentation from an existing repository and is a peer workflow, not an automatic handoff to `plan`.

## Workflow profiles

| | Classic | Advanced |
| --- | --- | --- |
| Best fit | Broad compatibility and explicit guidance | Advanced models that can operate from compact, independently owned skills |
| Availability | Every integration | Skills-based integrations only |
| Generated surface | Agent-native `sp-*` skills or `/sp.*` commands | Independent `spx-*` skills plus the original Classic map companions |
| Prompt policy | Full tutorials, recovery guidance, and compatibility detail | Removes repetition and stable boilerplate while preserving state, recovery, side-effect, and final-claim gates |
| Default | Non-interactive default | Explicit opt-in with `--workflow-profile advanced` |

Advanced optimization has **no hard word or token ceiling**. It optimizes expression only after preserving workflow semantics. An Advanced install also includes the unchanged Classic `sp-map-scan`, `sp-map-build`, and `sp-map-update` companions so a lower-cost model can run the more explicit map workflow.

Install either profile explicitly:

```bash
specify init my-project --ai codex --workflow-profile classic
specify init another-project --ai codex --workflow-profile advanced
```

Profiles are additive for a skills-based integration. To keep both in one project:

```bash
specify init my-project --ai codex --workflow-profile classic
cd my-project
specify init --here --force --ai codex --workflow-profile advanced
```

Canonical workflow names are integration-neutral. Invocation syntax depends on the integration:

| Integration surface | Classic `specify` | Advanced `specify` | PRD reconstruction |
| --- | --- | --- | --- |
| Codex, Antigravity, Trae, and ZCode skills | `$sp-specify` | `$spx-specify` | `$sp-prd-scan -> $sp-prd-build` |
| Claude, Cursor, Grok, and Mistral Vibe skills | `/sp-specify` | `/spx-specify` | `/sp-prd-scan -> /sp-prd-build` |
| Kimi Code skills | `/skill:sp-specify` | `/skill:spx-specify` | `/skill:sp-prd-scan -> /skill:sp-prd-build` |
| Slash-dot command integrations | `/sp.specify` | Not available | `/sp.prd-scan -> /sp.prd-build` |

`/sp-*` is not universal for skills-backed integrations. Use the invocation form generated for your selected tool—for example `$sp-plan`, `/skill:sp-plan`, or `/sp.plan`.

## Supported integrations

The current registry is the source of the following integration keys:

| Surface | Integration keys |
| --- | --- |
| Skills-based; Classic and Advanced | `agy`, `claude`, `codex`, `cursor-agent`, `grok`, `kimi`, `trae`, `vibe`, `zcode` |
| Command, prompt, or workflow based; Classic | `amp`, `auggie`, `bob`, `codebuddy`, `copilot`, `forge`, `gemini`, `iflow`, `junie`, `kilocode`, `kiro-cli`, `mimo`, `opencode`, `pi`, `qodercli`, `qwen`, `roo`, `shai`, `tabnine`, `windsurf` |
| Bring your own agent | `generic` with `--ai-commands-dir <directory>` |

Run `specify init --help` for the authoritative list shipped by the installed CLI. `specify integration list` inspects integrations already installed in a generated project; it is not the pre-init discovery command.

## Installation, upgrade, and repair

| Goal | Command or guide |
| --- | --- |
| Persistent Git install | `uv tool install specify-cli --from git+https://github.com/chenziyang110/spec-kit-plus.git` |
| One-time execution | `uvx --refresh --from git+https://github.com/chenziyang110/spec-kit-plus.git specify ...` |
| Upgrade to the current repository head | `uv tool install specify-cli --force --from git+https://github.com/chenziyang110/spec-kit-plus.git` |
| Pin a release | Append `@vX.Y.Z` from [Releases](https://github.com/chenziyang110/spec-kit-plus/releases) to the Git URL |
| Repair runtime-managed generated assets | `specify integration repair` from the generated project root |
| Diagnose tools and project compatibility | `specify check` |
| Troubleshoot installation and PATH | [Installation Guide](docs/installation.md) and [Upgrade Guide](docs/upgrade.md) |

`specify version` reports package and interpreter information, but development installs can share the same `.dev0` version across commits. Verify the active command surface with `specify --help`; on Windows, use `Get-Command specify -All` to find stale pip, Conda, or uv entrypoints that may shadow the intended executable.

Core scaffolding assets are bundled in the Python package. Tagged releases also
publish matching prebuilt `specify-runtime` binaries for Windows, Linux, and
macOS. `specify init` downloads and pins the matching runtime when possible and
reports a recovery path when the best-effort install is unavailable.

If `cognition init-empty` reports `unsupported_legacy_runtime`, a legacy
`.specify/project-cognition/` store is blocking the current schema; it does not
mean the runtime binary is missing. Archive that directory first (or remove it
only after confirming it is disposable), then rerun initialization for an empty
project or run `sp-map-scan -> sp-map-build` for an existing codebase.

## Documentation

| Goal | Read |
| --- | --- |
| Complete the first workflow | [Quick Start Guide](docs/quickstart.md) |
| Browse all guides | [Documentation Index](docs/index.md) |
| Install, pin, or troubleshoot the CLI | [Installation Guide](docs/installation.md) |
| Upgrade the CLI or a generated project | [Upgrade Guide](docs/upgrade.md) |
| Understand architecture and change propagation | [Project Handbook](PROJECT-HANDBOOK.md) |
| Audit project cognition compatibility | [Project Cognition Compatibility Inventory](docs/project-cognition-compatibility-inventory.md) |
| Maintain workflow/profile product contracts | [Repository agent guidance](AGENTS.md) |
| Choose project governance defaults | [Constitution Profiles](docs/constitution-profiles.md) |
| Develop an extension | [Extension Development Guide](extensions/EXTENSION-DEVELOPMENT-GUIDE.md) and [API Reference](extensions/EXTENSION-API-REFERENCE.md) |
| Build or publish presets | [Preset Guide](presets/README.md) and [Publishing Guide](presets/PUBLISHING.md) |
| Develop this repository | [Local Development Guide](docs/local-development.md) |
| Review workflow quality evidence | [Workflow Quality](docs/workflow-quality/README.md) |

## Project scope

- Python support starts at 3.11; CI exercises Python 3.11, 3.12, and 3.13.
- Generated automation includes Bash and PowerShell variants.
- Classic and Advanced are separate prompt products over shared CLI, schema, validator, and artifact contracts.
- In a terminal, the optional Codex team runtime is operated through `specify sp-teams ...`; inside Codex, `$sp-teams` is the generated skill entrypoint.
- The current `sp-teams` scope is Codex-only and optional. Other integrations do not receive the Codex team runtime by default.
- Project Cognition is advisory navigation, not repository truth: map points, code proves.

## Community and contributing

- Ask focused usage questions, report reproducible bugs, or propose features through [GitHub Issues](https://github.com/chenziyang110/spec-kit-plus/issues).
- Check [Releases](https://github.com/chenziyang110/spec-kit-plus/releases) before reporting an issue against an older build.
- Read the [Local Development Guide](docs/local-development.md) and the repository [pull request template](.github/PULL_REQUEST_TEMPLATE.md) before submitting a change.

The primary local verification loop is:

```bash
uv sync --extra test
uvx ruff check src/
uv run pytest -n auto
```

Pull requests should describe the change, record verification, and disclose AI assistance as requested by the repository template.

## License and acknowledgements

Spec Kit Plus is distributed under the [MIT License](LICENSE). It builds on [GitHub Spec Kit](https://github.com/github/spec-kit) and retains its upstream copyright notice.

## Maintainer reference

The repository's regression suite treats the detailed workflow and runtime rules below as a user-visible product contract. They remain searchable here but are collapsed so the primary README path stays focused on evaluation and first success.

<details>
<summary><strong>Expand the full workflow and runtime contract reference</strong></summary>

## Full product contract reference

`spec-kit-plus` is an independently developed Spec-Driven Development system focused on practical workflow support for local AI coding agents.

`specify` is the setup and management CLI. Inside a generated project, the
agent-native `sp-specify` / `spx-specify` workflow runs the brainstorming lock
flow, persists facts, route, and intent truth, and produces the structured
handoff for `plan`; later stages continue through `tasks`, `implement`,
integrated system `review`, and human `accept`.

This repository contains:

- the `specify` CLI
- built-in spec, plan, tasks, and implement templates
- agent integrations for tools such as Codex, Claude, Gemini, Copilot, Cursor, Windsurf, Kimi, MiMo Code, Forge, and others
- the bundled scripts and assets used by `specify init`

Project cognition navigation responses expose a machine-readable `epistemic_contract` with `graph_role=route_candidate_only`, `fact_source_of_truth=live_repository`, `live_verification_required=true`, `graph_only_claims_allowed=false`, and `unverified_claim_action=withhold`. The graph narrows evidence reads; it cannot authorize source changes or prove current behavior, and contradictory live evidence overrides the route candidate.

Graph claims are indexed assertions. Their lifecycle is `candidate`, `supported`, `verified_in_graph_generation`, `contradicted`, or `stale`; even `verified_in_graph_generation` is scoped to the active graph generation and is not current repository truth. Graph claims cannot authorize source changes and cannot set workflow `claim_ready=true`; bounded live evidence, matching workflow verification, and explicit final-claim authorization remain separate requirements.

Schema v5 adds revision-bound, expiring reconciliation to the auditable live feedback loop and current evidence basis while retaining superseded claim evidence as history. When claim-specific bounded reads settle a stale or contradicted route, provide semantic intent in memory and run `specify-runtime cognition claim-reconcile prepare --input-json '<intent-json>' --format json`; never create an intent file. The runtime owns every integrity field and returns the prepared packet path plus structured `apply_argv`. Execute that argv through `specify-runtime cognition claim-reconcile apply --input <prepared_packet_path> --format json`, then rerun Compass once on ready. Reconciliation remains route-candidate evidence and never grants workflow final-claim authorization. Schema v5 is current-only and does not migrate schema v4 or older databases.

## Install

### Persistent install

Install the CLI from this repository:

```bash
uv tool install specify-cli --from git+https://github.com/chenziyang110/spec-kit-plus.git
```

Upgrade to the latest Spec Kit Plus version. If a machine previously installed
`specify-cli` through `pip`, Conda, or another `uv tool` location, remove the old
entry first so a stale `specify.exe` does not shadow the new one:

```powershell
python -m pip uninstall -y specify-cli
uv tool install specify-cli --force --from git+https://github.com/chenziyang110/spec-kit-plus.git
Get-Command specify -All
specify --help
```

`specify version` reports the package version, but development installs can share
the same `.dev0` version string across commits. Use `specify --help` to confirm
the expected command surface, and use `Get-Command specify -All` on Windows to
detect duplicate old entrypoints.
Feature creation follows `sp-specify` plus the generated create-feature script
at `.specify/scripts/bash/create-new-feature.sh` or
`.specify/scripts/powershell/create-new-feature.ps1`; do not assume a separate
`specify create-feature` command family exists. Generated feature workspaces
default to `YYYY-MM-DD-<slug>` names; numeric prefixes are legacy and require
the script's explicit `--number` / `-Number` option.

### One-time use without installing

```bash
uvx --refresh --from git+https://github.com/chenziyang110/spec-kit-plus.git specify init my-project --ai codex
```

Initialize the current directory with the latest repository version, without relying on whatever `specify` is currently on your `PATH`:

```bash
uvx --refresh --from git+https://github.com/chenziyang110/spec-kit-plus.git specify init . --ai codex
```

### Local editable install for development

```bash
git clone https://github.com/chenziyang110/spec-kit-plus.git
cd spec-kit-plus
uv sync --extra test
uv run specify --help
```

## Prerequisites

- Python 3.11+
- `uv`
- `git`
- your target AI agent CLI or IDE integration

## Classic quick-start contract

Create a new project:

```bash
specify init my-project --ai codex
```

Skills-based integrations offer one workflow prompt profile per init run:

```bash
# Current full workflow skill set (default for non-interactive compatibility)
specify init my-project --ai codex --workflow-profile classic

# Concise, independent SPX skills for advanced models
specify init my-project --ai codex --workflow-profile advanced
```

Interactive init asks which profile to install. One run installs exactly one
profile. To keep both in the same project, run init again with `--here --force`
and select the other profile; the second run adds it without removing the first.
The advanced profile is available only for skills-based integrations.

Use a non-default built-in constitution profile when the repo needs a different
governance default:

```bash
specify init my-project --ai claude --constitution-profile library
```

Initialize the current directory:

```bash
specify init --here --ai codex
```

If the current directory is not empty:

```bash
specify init --here --force --ai codex
```

Generated projects may also persist a trusted project launcher in
`.specify/config.json` under `specify_launcher`. When that launcher exists,
first-party runtime helper instructions should follow it instead of assuming the
first `specify` executable on PATH is the correct one.

Validate generated-project runtime health and repair stale generated assets:

```bash
specify check
specify integration repair
```

`specify check` now reports:

- missing or broken persisted project launchers
- stale generated PowerShell workflow scripts that still rely on exact branch-to-feature-dir matching
- stale Claude hook commands that still use shell-parsed direct Python, POSIX, cmd, or PowerShell-style launchers instead of the shell-free Node launcher
- personal Claude workflow skills (`sp-*` / `spx-*`) whose names collide with project-installed Spec Kit skills; Claude gives the personal copy precedence, so this is a repairable block rather than a harmless duplicate

`specify integration repair` refreshes shared/runtime-managed generated assets in place
without overwriting user-edited workflow or skill content. It never moves or
rewrites personal Claude skills. When a collision is reported, back up and move
the matching directory out of `~/.claude/skills/` (or
`$CLAUDE_CONFIG_DIR/skills/`), fully restart Claude Code, and rerun
`specify check`.

Validate the installation:

```bash
specify --help
specify check
```

## Common Agent Examples

Codex:

```bash
specify init my-project --ai codex
```

Claude:

```bash
specify init my-project --ai claude
```

Claude project-local installs now write `.claude/skills/` as before and also
install thin native hook adapters under `.claude/hooks/`. When
`.claude/settings.json` is absent, it is created; when it already exists and is
valid JSON, managed hook registrations are merged without overwriting unrelated
user settings.

If a generated Claude project on Windows still has stale hook commands, run:

```bash
specify integration repair --script ps
```

Gemini:

```bash
specify init my-project --ai gemini
```

Copilot:

```bash
specify init my-project --ai copilot
```

Cursor:

```bash
specify init my-project --ai cursor-agent
```

ZCode:

```bash
specify init my-project --ai zcode
```

Grok:

```bash
specify init my-project --ai grok
```

MiMo Code:

```bash
specify init my-project --ai mimo
```

If you want templates without checking whether the agent tool is installed:

```bash
specify init my-project --ai codex --ignore-agent-tools
```

## Workflow

After a classic-profile `specify init`, use the generated workflow commands in
your agent:

1. `constitution` to establish or revise project principles when the seeded default constitution needs project-specific changes
2. `specify` to produce a planning-ready, analysis-first feature spec
3. `plan` to define implementation design
4. `tasks` to break work into executable tasks
5. `implement` to execute the task plan
6. `review` to start the integrated product from its official entrypoint, repair bounded wiring or implementation defects, and capture fresh system evidence
7. `accept` to restore a human's context and guide explicit product acceptance one real step at a time
8. `auto` to resume the recommended next workflow step from current repository state when you do not want to name the exact command yourself

Launch-capable integrations treat every invocation as an independent Run. With
the default `--workspace-policy auto`, exactly one non-overlapping modifying Run
uses the primary workspace when that checkout is pristine; every overlap, and
every launch that finds idle but unsealed local changes, receives an isolated Git
worktree. Overlaps clone the primary Run's pre-launch Snapshot. The supervisor
forces the child agent's working directory, maintains liveness, releases primary
ownership on every terminal path, and fences an interrupted Attempt before a
replacement generation can start. A successful Run seals an immutable Result.
Host adapters normally queue and start the child in one call through
`specify-runtime run launch ... -- <agent argv>`; the full tokenized contract is
discoverable through `api show run.launch`. `run supervise <run-id> ...` remains
the replacement-attempt path for a previously queued or interrupted Run.
Both commands accept either a canonical compiled WorkerTaskPacket receipt through
`--work-packet-file <path> --work-packet-sha256 <sha256>` or the manual
`--work-agent-id`, `--work-task-ref`, `--work-summary`, and
`--work-intents-json` fields. Packet-backed launch verifies the exact compiled
bytes before parsing, then derives the task identity, objective, and confirmed
`scope.write_scope` so adapters do not rebuild the same metadata. The supervisor publishes
the Work item before the child starts and exports `SPECIFY_WORK_ID`,
`SPECIFY_WORK_FENCE`, and `SPECIFY_FEATURE_BRANCH_POLICY` to the managed child.
On Windows, the supervisor also extends `WSLENV` so the same fenced Run binding
survives when the child invokes WSL-backed Bash helpers.

Modifying agents also coordinate through the repository-shared Work Board in
`run-control.sqlite`. A managed `run launch` or `run supervise` automatically
reconciles expired leases, registers its Work item, renews the lease, completes
it on success, retains it as blocked on nonzero exit, and records cancellation
as interrupted before returning. Unhosted agents use `specify-runtime board
reconcile`, inspect current ownership with `board show` or `board owner`, and
register planned file or directory writes with `work begin`. Later scope
expansion is an atomic `work scope-add`; checkpoints renew the lease, and finish
or abandon releases the scope without erasing history.
Same-path and ancestor/descendant overlaps are blocked. If a lease expires,
clean scope is released, while matching dirty changes—or an unavailable worker
worktree—remain behind a recovery hold until explicit `work resume` or
`work abandon`. After a confirmed computer/session shutdown, `work interrupt`
can inspect and fence the still-live record immediately instead of waiting for
lease expiry; it must never be used to take over an owner that may still be
running. The board is a CLI projection and must not be edited by hand.
Before an unhosted `sp-specify` writes anything, the feature script runs in
read-only dry-run mode and its exact feature id/directory is registered through
the single `specify-runtime board feature-bootstrap` command. That command
returns the Work fence and branch policy, preventing two callers from both
observing an empty board before either advertises its work. The real script
replays the resolved feature id; `keep-current` avoids a branch switch, while an
idle `default` path preserves the historical business-branch behavior. Managed
Runs always remain on their allocated private/current ref regardless of the
public policy. Existing feature directories are rejected unless explicit resume
was requested. Run Control's private `specify/runs/*` isolation branches remain
independent.

Delivery is a separate frozen chain: inspect sealed work with
`specify-runtime result show`, compose one or more eligible Results with
`specify-runtime candidate build`, prove that exact Candidate with `candidate
review`, record only an actual human decision with `accept receipt`, publish
under target-ref compare-and-swap protection with `cas publish`, then update the
primary workspace separately with `sync safe`. Publication recognizes the exact
sealed primary Result as accounted Run state, but any additional index or
worktree change blocks publication and remains untouched. Five concurrent `sp-quick`,
`sp-debug`, or formal workflow Runs therefore never share an overlapping writable
workspace or silently merge into one another. Publish and sync wait for the
primary-workspace ownership slot to be idle; both use durable receipts so an
interruption can be reconciled without repeating an unproven mutation.

After an advanced-profile init, use independent, discoverable SPX skills:

```text
$spx-accept               $spx-analyze              $spx-ask
$spx-auto                 $spx-checklist
$spx-constitution         $spx-debug                $spx-deep-research
$spx-design               $spx-discussion           $spx-explain
$spx-fast                 $spx-implement            $spx-implement-teams
$spx-map-build            $spx-map-rebuild          $spx-map-scan
$spx-map-update           $spx-plan                 $spx-prd
$spx-prd-build            $spx-prd-scan             $spx-quick
$spx-research             $spx-specify              $spx-tasks
$spx-taskstoissues        $spx-team                 $spx-test-design
```

Advanced installs also include the unchanged Classic map companions:

```text
$sp-map-scan              $sp-map-build             $sp-map-update
```

Use the concise `spx-map-*` skills when an advanced model owns the map
workflow. Use the original `sp-map-*` skills when a lower-cost model should run
the established, more explicit scan/build/update contract. These companions are
generated from the same Classic command templates; they are not SPX rewrites.

Invocation punctuation depends on the agent (`$spx-plan`, `/spx-plan`, or
`/skill:spx-plan`). Each skill is a native catalog entry and loads only its own
compact owning prompt plus triggered advanced references. SPX has no hard word
or token ceiling: prompt optimization removes repetition, tutorials, and stable
boilerplate only after preserving every Classic stage input, triggered output,
state owner, resume transition, blocker/recovery rule, side-effect gate, and
final-claim gate. The advanced profile is command-equivalent and
prompt-optimized: every Classic command keeps an independent SPX entrypoint,
state owner, write boundary, resumable stop point, and explicit side-effect
gate. The normal feature path is
`spx-specify -> spx-plan -> [spx-test-design] -> spx-tasks -> spx-implement -> spx-review -> spx-accept`; test design is optional on that default formal path, while its independent producer can publish typed Plan, Quick, Tasks, or Review projections without waiting for Plan completion. Focused specification repair stays inside `spx-specify`. Discussion (including an optional confirmed handoff into `spx-quick` or `spx-specify`), research, analysis, checklists, issue export, team execution, PRD reconstruction, and map phases remain separately invocable instead of being hidden inside that path. Integrated system verification belongs to `spx-review`, not a standalone workflow. `spx-fast` is for trivial leader-direct changes with consume-only Learning, Project Cognition, targeted verification, and one lightweight self-review; `spx-quick` is a resumable direct-delivery workflow for clear requests
that do not need the formal specification path first, including larger work
when task-local planning, lanes or batches, consequence tracking, and validation
can preserve acceptance confidence.

`sp-accept` / `spx-accept` is deliberately separate from implementation's
internal code review. Successful technical closeout prepares a fingerprinted
`human-acceptance.json`; the acceptance agent assumes the human remembers
nothing, explains what changed and why it matters, then leads one real product
step at a time with an expected visible result and safe failure branch. Human
PASS is required for every mandatory scenario. Failures preserve evidence and
return to implement/debug or upstream requirements instead of being silently
fixed inside acceptance.

Classic and Advanced also share one blocked-exit contract. A blocked workflow
must identify the exact stage, cause, owner, sanitized evidence, recovery
already attempted, affected scope, smallest next action, observable unblock
criteria, and exact resume point; an error list or “ask a human” is not a valid
blocked result. Ordinary repository repair and available fallbacks stay
agent-owned. When credentials, protected external systems, external-write
approval, subjective product/visual decisions, or physical access genuinely
require a person, the response expands into a step-by-step Human Action Guide
with prerequisites, safety notes, exact clicks or commands, expected results,
failure branches, verification, sanitized evidence to return, and the resume
command. Protected CI guidance must bind the repository, branch, commit,
pipeline/job, authorization boundary, and returned pipeline URL or ID rather
than merely saying that CI remains to be run.

SPX references are profile-local under `templates/advanced-skills/` and never
copy or include classic `templates/command-references/`. The three separately
installed Classic map companions retain their original command-reference
sidecars. A dedicated SPX reference is added only when another execution tier
needs a stable contract, such as the low-cost scan worker; deterministic
artifact schemas remain in the runtime or renderer instead of being repeated as
prompt prose. Compact advanced Markdown views live beside each skill, while
canonical JSON schemas, validators, state machines, and project-cognition remain
shared single sources of truth.
`templates/advanced-skills/_shared/surface-map.json` records the deterministic
one-to-one Classic-to-Advanced command mapping and guards against accidental
omissions.
The classic passive-skill prompt bundle is not copied into an advanced install;
essential TDD, verification, security/consequence, delegation, and map gates are
compiled into the relevant hot path or loaded as a triggered advanced reference.

Project cognition is the advanced profile's default navigation data plane.
SPX uses Compass to select minimal live reads and verification routes, then
proves claims from the live repository. Writing workflows update cognition
after verified source/runtime changes; the map skills are reserved for explicit
maintenance or a genuinely rebuild-required baseline. SPX reuses existing
`.specify` scripts, artifacts, and canonical `/sp.*` state identifiers rather
than introducing another runtime format.

Map reconstruction also preserves independent commands. `spx-map-scan` resolves
the canonical boundary, creates strict packets of at most 25 concrete paths by
default, routes bulk reads to the lowest-cost capable worker model, accepts each
packet, and stops after scan validation. `spx-map-build` consumes only that
frozen evidence and runs deterministic `build-from-scan` plus build validation;
it is not a second model-driven repository scan. `spx-map-rebuild` is only the
optional convenience orchestrator for those two skills.
For a lower-cost model, invoke the additionally installed original
`sp-map-scan -> sp-map-build` workflow and use `sp-map-update` for incremental
maintenance; those skills remain byte-equivalent to a Classic-profile install
in the same project.

Advanced optimization removes repeated cognition tutorials, fixed role chains,
mandatory delegation where leader-direct work is safer, long examples, and
model-authored copies of stable schemas or boilerplate. It does not remove
independent commands, lifecycle boundaries, read-only gates, external-write
authorization, scan/build isolation, or recoverable state. Codex and Claude use
their respective durable-team backends for `spx-implement-teams`; unsupported
integrations refuse that backend explicitly. `spx-team` remains the Codex-only
runtime operations entrypoint. Classic assets and behavior remain unchanged
when the `classic` profile is selected.

- `design` / `sp-design` and Advanced `$spx-design` use `specify-runtime design`
  as one natural-language UI-change entrypoint that routes `create/refine/audit`;
  reference synthesis is an input strategy for create/refine rather than another
  public command or terminal task type. On a design-first route the first formal
  consumer is `sp-specify`. When Design follows an already planning-ready source
  spec and requirements remain unchanged, `formal-post-specify` binds a late
  Design overlay to that exact source digest and returns directly to Plan
  (`specify -> design -> plan`) without a second Specify. Only a real
  requirements/scope/acceptance change reopens Specify. `sp-quick` may pin the
  same registered change for direct delivery.
  A later approval must not silently retarget an active formal feature or Quick
  workspace; adoption is explicit through Specify rebinding or a confirmed
  Quick checkpoint amendment.
  A new bounded direction starts with `specify-runtime design change UD-####`;
  refinement of registered truth starts with
  `specify-runtime design iterate <SOURCE-UD-ID> <SUCCESSOR-UD-ID>`, which pins
  exact lineage and source bytes. Each change owns
  `.specify/design/changes/<UD-ID>/DESIGN.md`, its brief, previews, approval,
  handoff, and exported `design-contract.json`. Approved changes become
  consumable only after `specify-runtime design register`; the metadata-only
  `.specify/design/index.json` records scope, relationships, status, exact path,
  and the registered document digest. A root `DESIGN.md` is read-only legacy
  input when present and is never created or silently rewritten by init.
  `specify-runtime design resolve --scope <exact-surface>` discovers active
  candidates without adopting them. Current binding artifacts are singular, so
  composite coverage is split into independently bound consumer units, each
  with one exact scope and one binding file.
  `specify-runtime design diff <CURRENT-UD-ID> <CANDIDATE-UD-ID>`
  exposes the semantic delta; read-only `specify-runtime design impact
  <consumer-ref> ... --expected-change <CURRENT-UD-ID|none>` then classifies the
  exact scope's visual/interaction/component/responsive/content and stable
  `DS-*`/`DH-*` impact, returning `preserved_bindings`,
  `invalidated_bindings`, and `reconcile_from` before the consumer updates its binding artifact,
  and `specify-runtime design adopt ... --expected-change <CURRENT-UD-ID|none>`
  records the formal or Quick compare-and-swap after those bytes are updated.
  Its receipt repeats the impact contract so the owning workflow reconciles
  only affected stages and Review evidence, preserves completed work, and never
  lets the design runtime rewrite consumer artifacts. Quick additionally
  retires unstarted affected packets and creates a corrective work item for
  completed-work drift.
  Use the design workflow for new product UI, redesigns,
  rebrands, core workflow experience, multi-platform interface decisions, and
  high-visibility customer-facing surfaces. Visual create and scope-changing
  refine require durable taste intake in the design brief (one-line design
  read, variance/motion/density dials, aesthetic family, foundation strategy,
  redesign mode, surface-aware anti-slop locks, and optional synthesize
  reference-board intents). The Agent asks one unresolved, high-impact design
  question at a time, recommends a grounded default, and probes live image
  generation, inspection, and editing capabilities independently. Generation
  available produces one image-primary board bound to its exact prompt and
  manifest; otherwise the Agent authors one self-contained HTML-primary
  concept. User feedback revises
  that same direction in a new round until the user explicitly approves it;
  ready-level `design preview-lint` rejects unconfigured scaffold output.
  Approval freezes one
  exact direction with a byte-bound approval sidecar plus visual/manifest
  digests, the prompt digest for image-primary rounds, an immutable
  `.handoff.json` sidecar and digest, stable `DS-*`
  decision IDs, and stable `DH-*` implementation contract IDs. Downstream
  artifacts reference those IDs instead of rewriting design intent. Rejecting
  or revising that direction produces a new review round; an
  approved round is never edited in place. Design-library aesthetic seeds and
  `anti-slop-policy.md` are inspiration only and never substitute for
  `design approve`.

  The shared **UI Professional Skill** pack adds progressive disclosure to this
  studio loop. Its compact router selects one product domain, at most one visual
  style, and at most two specialist skills, then loads only those exact
  references. The resolved route is pinned to the current immutable round;
  material ambiguity produces one direction-changing question. Approved
  references remain authoritative, and image-primary versus HTML-primary
  authoring receives separate prompt augmentation. For Web UI, the same router
  emits a stack-compatible `mature_web_ui_resource_ids` shortlist and opens a
  component-selection gate: reuse live components first, prefer one mature
  primary system, add only capability-justified headless/specialist libraries,
  and load official Agent/MCP/LLM material only for selected candidates. A
  bounded project-root scan records manifests, installed systems, component
  roots, tokens, themes, and entry surfaces; deterministic scores return compact
  reason/confirmation codes, while routed `smoothness_acceptance_ids` flow into
  the existing usability and Review evidence contract.
  Live product UI is the default style authority: feature, component, and
  partial functional-page work uses `inherit-existing`, cites exact live source
  refs, protects `global-shell` and `shared-components`, permits no style delta,
  and selects no style skill. Only explicit authorization for one exact complete
  page may use `page-overhaul-authorized`; the authorization never expands to
  shell, shared components, or sibling pages. This structured authority is
  carried unchanged through downstream UI contracts.

**Design Governance Foundation v1.0** remains the frozen preview-quality
contract: AI design
artifacts are validated for deliverable quality, not only renderability—taste
intake, structural/semantic/quality layers, diagnostic recovery, and a Golden
Artifact Set as regression truth. Preview boards are freeform single-concept
canvases (not fixed product specimen templates); agents replace the seed with
one image-primary board when generation is live or project-specific HTML
otherwise, while the manifest and ready lint enforce governance. Do not stack new ready-gate conditions
without a layer, recovery path, diagnostic contract, and golden fixture. Full
constraint text lives in `PROJECT-HANDBOOK.md` under
`Design Governance Foundation v1.0`. Baseline fixtures:
`tests/fixtures/design-preview/`.

**Design Governance Foundation v2.0** governs ownership and consumption: every
approved direction is an immutable, bounded UI change (`UD-*`), overlapping
active scopes require an explicit `supersedes` relationship, consumers pin the
registered path and SHA-256 instead of resolving “latest”, and only durable
cross-change invariants graduate to project rules. See
`docs/adr/0001-change-scoped-ui-design-contracts.md`. Scope-aware successors,
partial `superseded_scopes`, semantic diff, and explicit adoption are governed
by `docs/adr/0002-scope-aware-ui-design-iteration.md`.

Substantive feature UI is handled during `sp-specify`/`$spx-specify` even when
no screenshot is supplied: it produces a feature `ui-brief.md` that carries
experience intent, hierarchy, states, responsive/accessibility behavior, and
visual acceptance through plan, task, and implementation contracts. When a
request includes screenshots, mockups, design exports, URLs, existing pages, or
"make it like this" language, Classic additionally uses the CLI-owned
`ui-reference-artifact` lane: it submits reference notes/briefs through their
registered artifact owners, imports binary attachments through `specify-runtime
evidence import`, and defaults fidelity to `approximate`.
Implementation closes with a real-entrypoint capture, visual inspection,
repair, and recapture loop. If comparison is unavailable, fidelity remains
`pending-human-review` instead of being claimed as complete.

For generated Classic SKILL integrations, passive model invocation has one exact
allowlist: `sp-discussion`, `sp-quick`, `sp-debug`, and `sp-fast`. Every other
`sp-*` skill is user-invoked only; agents may recommend its projected command but
must stop until the user invokes it. Resuming a workflow the user already invoked
does not reopen the passive-entry decision.

Use `ask` for read-only evidence-backed project Q&A when you need a direct answer from project files, templates, docs, state, or memory before choosing an action workflow. Project cognition guides the search; live evidence proves the answer. Same-topic follow-ups reuse the prior evidence set when it still applies, localized or project-slang terms are normalized into project vocabulary, and complex answers separate proven facts from evidence-derived inferences. In v1, `sp-ask` is independent from `sp-discussion`, creates no state or handoff, makes no source edits, and does not run tests, builds, package managers, or project CLI commands by default. There is no `specify ask` Typer helper in v1.

Use `discussion` before `specify` or `quick` when product direction, trade-offs, or context boundaries are not yet stable. Human-visible replies remain human-first and adaptive; compact typed state stays backstage. An already-invoked incomplete discussion remains active across topical follow-up turns even when the user does not repeat the workflow name. After explicit handoff request and boundary lock, `sp-discussion` writes and draft-validates exactly one Agent-only `handoff-to-specify.json`, presents its `review_digest`, binds exact user approval with `discussion confirm-handoff`, and only then marks the contract ready. It has no Markdown companion, assessment document, or reviewer-guide artifact. The contract preserves target need, scope, constraints, success criteria, design direction, evidence refs, target boundary, decision digest, Must-Preserve/Consequence refs, consumer eligibility, and recovery. Supporting discussion files are read downstream only through a named stale, missing, or contradictory evidence ref.

The discussion output is one canonical Agent-only JSON contract shared by eligible consumers.

`sp-discussion` continues by default, uses recommendation-first progression, and asks only for user-owned decisions. Its Context Boundary Gate locks the target project root before project-specific claims; current-project cognition is advisory navigation and cannot prove another project's implementation facts.

The discussion workflow must continue by default, do not ask for continuation, and ask only when user judgment is genuinely required and no safe default exists.

The main pipeline now uses one authority per phase: `handoff-to-specify.json` -> `spec-contract.json` -> `plan-contract.json` -> `task-index.json` -> per-task lifecycle records -> `implementation-handoff.json` -> `review-state.json` -> `human-acceptance.json`. Project-facing Markdown is rendered only when it has independent human/repository value. Delegated packets are compiled just in time and task review remains evidence-triggered inside Implement. Mandatory system Review uses a Leader to freeze the Review Universe, join independent Audit results, dispatch isolated Fix subagents, and assign independent Revalidation; approval requires zero uncovered scope and fresh real-entrypoint evidence before human acceptance.

When a discussion direction is locked but the topic is not handoff-ready or downstream-ready, `sp-discussion` should use the same unified frontstage contract to include the locked direction, reason, blocked decisions, evidence gaps, downstream planning inputs to preserve, default discussion action, and override path instead of returning only state updates or waiting for the user to ask for "next". It must not split the work into P0/P1/P2, migration phases, release batches, task packets, or ordered implementation steps; those belong to Quick task-local planning when Quick is selected, or to `sp-plan`, `sp-tasks`, and `sp-implement` on the formal path.

When the user rejects fallback, backup plans, dual-stack operation, or old-implementation fallback, `sp-discussion` should record that as no parallel old-backend operation, no old-stack cutover fallback, and no alternate product path. It should not turn that into a new discussion question about database snapshots, restore mechanics, rollback scripts, or other data-safety mechanisms; those are downstream planning and implementation safety constraints, not product fallback options.

When a discussion looks mature enough for handoff but the user has not explicitly requested handoff, `sp-discussion` should use the same unified frontstage contract to give the likely assessment verdict, proposed handoff goal, recommended consumer, package scope, excluded scope, readiness checks, default next action, and override path without creating a separate assessment artifact.

When a draft contract exists, `sp-discussion` explains the proposed route, scope, exclusions, readiness checks, and allowed review decisions in the visible reply. The reply is human-first; the JSON remains the only handoff authority.

When review returns `request-changes` or a consumer reports `blocked_by_handoff_integrity`, `sp-discussion` resubmits the repaired contract inline through `specify-runtime discussion write-handoff`, reruns `validate-handoff`, and confirms the new returned `review_digest`. Consumers block rather than reconstruct or patch upstream truth.

When `sp-specify` consumes a user-confirmed discussion contract, it enters compile mode, creates an absent `spec-contract.json` through `specify-runtime artifact scaffold --kind spec-contract`, and fills only targeted JSON pointers through leased `artifact patch` calls without repeating settled choices. It never submits or reconstructs the whole fixed contract. User review is required only for a non-empty semantic delta or a real unresolved user-owned decision; conditional project-facing artifacts are not universal gates.

When `sp-discussion` recommends a default next step, the same reply should include the first-pass content for that step, such as a draft, option board, readiness checklist, handoff assessment checklist, evidence plan, or field-by-field responsibility audit table. It should not make the user ask for "next" just to see the content it already recommended.

When `sp-specify` consumes a confirmed discussion contract, it preserves the decision digest by stable reference and writes `spec-contract.json`. When `sp-quick` consumes it with no semantic delta, it seeds `STATUS.md` and reuses the confirmed digest instead of presenting a duplicate Quick confirmation.

Generated workflows preserve the user's complete user-confirmed scope. Scope reduction requires user confirmation: agents should not steer a requirement toward an MVP, pilot, prototype, first-story release, future-work delivery slice, agent-invented `v1/v2`, agent-invented `P0/P1`, or smaller validation build unless the user asked for that shape, the request already defines that boundary, or a named constraint makes reduced scope a decision the user confirms. Complexity alone is not a valid reason to shrink, defer, or block ordinary work; `sp-plan` and `sp-tasks` should use sequencing, dependencies, batches, join points, refinement checkpoints, and validation paths. Runtime capability limits are blockers only under the adaptive execution policy for heavy, safety-critical, or unpacketizable work, and they do not reduce scope.

`implement` validates the task-graph revision before starting and runs review only on repository/task drift, parallel joins, write-scope drift, validation failure, worker concern, obligation conflict, real-entrypoint gaps, or review-window limits. It records the result in one task lifecycle record instead of separate briefs, review packages, and ledgers. A mandatory protected-CI, remote-system, or human evidence gap stays as a structured blocked task; when a local commit is required only to obtain that evidence, `external-evidence-checkpoint` permits a non-final checkpoint without accepting the task, resolving the tracker, authorizing push/CI, or weakening final closeout. Product goal, scope, architecture, required evidence, `MP-*`, `CA-###`, and feasibility conflicts still route back to the owning upstream workflow.

After technical closeout, `accept` is the default human-facing stage. It reads the fingerprinted implementation summary, assumes the human has no prior context, explains the delivered outcome and exact entrypoint, and leads one required scenario step at a time. It writes only `human-acceptance.json` plus acceptance-owned workflow state. An explicit human PASS is required; defects and requirement gaps are recorded and handed back to their owning workflow.

Command-surface minimization must not delete capability. If upstream discussion or specification text includes a new/create/scaffold/authoring operation, later workflows must preserve it through an explicit public command, TUI route, core API, private helper, or user-confirmed deferral carrying confirmation source, exact excluded behavior, residual risk, reopen or stop condition, and downstream artifact. Static templates, manual copy steps, and template-only docs are supporting assets, not a substitute for the confirmed operation unless the user explicitly chose that narrower entry point.

For cross-project work, current project cognition cannot prove another project's files. Lock the target project root and record whether target evidence comes from target cognition, minimal live reads, user confirmation, external source, or explicit assumptions.

For an existing repository that needs product documentation rather than a new
change spec, use `prd-scan -> prd-build` as the canonical heavy reconstruction
PRD lane. It extracts repository-first current-state PRD evidence from
implementation reality and compiles a reconstruction archive with two reader
entry layers: `exports/README.md` as the package navigation entry and
`exports/prd.md` as the primary reader-facing PRD. It is a peer workflow path
to `specify` and does not automatically hand off to `plan`.
`prd` remains as a deprecated compatibility entrypoint only.

Built-in constitution profiles:

- `product` (default) for application and service repos
- `minimal` for lean, low-ceremony repos
- `library` for packages, SDKs, and CLIs with compatibility concerns
- `regulated` for security, privacy, or audit-heavy repos

Profile details and selection guidance live in [docs/constitution-profiles.md](docs/constitution-profiles.md).

Mainline pre-planning flow:

```text
specify -> plan
```

Feature creation is driven by the `specify` workflow itself. `sp-specify` now
uses a collaborative reviewed specification flow: explore project context,
ask one question at a time and compare approaches for raw discovery; a confirmed
discussion enters compile mode, reuses its decision digest, and skips repeated
questions or review when `semantic_delta` is empty. Use `sp-specify` with the generated create-feature script at
`.specify/scripts/bash/create-new-feature.sh` or
`.specify/scripts/powershell/create-new-feature.ps1`, plus the lane/runtime
helpers that it invokes; do not look for or teach a separate branch-creation
CLI family. The generated create-feature script defaults to
`YYYY-MM-DD-<slug>` feature workspace names; use its explicit numeric option
only for legacy sequential prefixes.

`specify` remains the public entry shell and writes canonical Agent-only
`spec-contract.json` plus project-facing `spec.md`. `alignment.md`, `context.md`,
`references.md`, and requirements diagnostics are emitted only when their
content has independent project-review value; `workflow-state.md` stays sparse
resume state. When a discussion selects the formal spec-first path, invoke
`sp-specify` with the handoff JSON path or discussion slug, or let it select the
single eligible unconsumed ready contract. When it selects direct delivery,
`sp-quick` binds the same contract and digest into task-local `STATUS.md` and
scales its own ordered work-item plan. Either consumer reads supporting
discussion files only when a named evidence ref is stale, missing, or
contradictory.
Capability operations, semantic decisions, protected obligation refs, and any
semantic delta live in `spec-contract.json`; ambiguous product terms such as "real",
"capability", "usable", fetch, probe, model, endpoint, `能力`, `真实`, and
`可用` must be decomposed before scope is narrowed.
Operation-shaped terms such as `new`, create, scaffold, authoring, CLI path,
and TUI path receive the same treatment: command-surface minimization must not
delete capability, and a manual copy or template-only interpretation requires
explicit user confirmation.

The normal next step remains exactly one of `/sp.plan`, `/sp.specify`, or
`/sp.deep-research`. `/sp.plan` is valid only after the written artifacts pass
self-review and user review has been requested.

Treat the live `specify --help` output as the only authoritative CLI command
surface. Before suggesting or running a `specify <subcommand>` invocation,
verify it exists in `specify --help` or `specify <subcommand> --help`, and do
not invent unsupported names such as `specify create-feature`.

### Agent-facing CLI discovery and workflow guard

Agents should start with `specify-runtime api handshake --format json` and use
`specify-runtime api list --format json` to discover the compact unified-runtime
surface. The remaining Python domain commands stay progressively discoverable:
`specify api commands --format json` inventories live Typer operations as
summary cards. Expand only a selected operation with
`specify api command <dot-separated-id> --format json`, or expand one Python
domain capability/schema with `specify api show` and `specify api schema`. This
keeps help text and parameters out of context until they are needed.

Feature phase order lives in CLI-owned `FEATURE_DIR/workflow.json`;
rich `workflow-state.md` remains workflow-owned evidence and Learning state.
Feature stages use `specify-runtime workflow show|enter|next|complete-stage|transition|reopen|block|resolve|closeout`.
After an active stage's artifacts pass, its owner runs `specify-runtime workflow complete-stage`
with the current revision. The destination stage then runs the exact returned
`specify-runtime workflow transition --to <stage>` argv. Only completed `accept` is
terminal. The CLI refuses skips or stale writes without mutation. Exit code `10` means a durable,
resumable business blocker, `2` means invalid usage, `1` means execution
failure, and `0` means success. Human-owned blockers include exact steps,
expected results, safe failure branches, evidence to return, and resume argv.
Evidence-backed `specify-runtime workflow reopen` handles an invalidated earlier or same
completed non-accept stage without deleting stale artifacts; failed acceptance
uses atomic `accept route-repair`. An unresolved blocker cannot be replaced or
bypassed. After its criteria are proven, `specify-runtime workflow resolve` reactivates the same
owner and preserves the complete blocker audit.

Optional feasibility branch when `sp-specify` finds an unproven implementation chain:

```text
specify -> deep-research -> plan
```

This branch is a runtime-enforced gate, not generic web research and not a
second specification phase. It binds the current `spec-contract.json` digest
and selected capability IDs, coordinates bounded track leases and results,
checks repository/external/spike provenance, preserves contradictions and
rejected attempts, requires independent audit, and publishes
`research/handoff-to-plan.json` with an exact digest and state revision.
`sp-plan` must verify that binding before consuming the `PH-###` decisions.
`deep-research.md` is only the derived human-readable projection. Minor changes
to already-proven capabilities use the runtime `not-needed` path or skip the
branch according to the spec gate.

### Workflow invocation syntax

Canonical workflow names are integration-neutral: `constitution`, `specify`,
`plan`, `tasks`, `implement`, `analyze`, and the other workflow names below are
the stable concepts used in docs, workflow state, and generated artifacts. The
text a user types in their AI agent depends on the integration.

Invocation syntax depends on the integration:

| Integration surface | Example: specify | Example: prd-scan -> prd-build | Example: plan | Notes |
| --- | --- | --- | --- | --- |
| Codex skills | `$sp-specify` | `$sp-prd-scan -> $sp-prd-build` | `$sp-plan` | Skills-backed Codex projects use `$sp-*`. |
| Antigravity skills | `$sp-specify` | `$sp-prd-scan -> $sp-prd-build` | `$sp-plan` | Antigravity projects install workflow skills under `.agents/skills`. |
| Kimi Code skills | `/skill:sp-specify` | `/skill:sp-prd-scan -> /skill:sp-prd-build` | `/skill:sp-plan` | Kimi exposes generated skills through `/skill:sp-*`. |
| Claude skills | `/sp-specify` | `/sp-prd-scan -> /sp-prd-build` | `/sp-plan` | Claude keeps slash-style skill commands. |
| Cursor skills | `/sp-specify` | `/sp-prd-scan -> /sp-prd-build` | `/sp-plan` | Cursor projects install workflow skills under `.cursor/skills` and keep `.cursor/rules/` for context files. |
| Grok skills | `/sp-specify` | `/sp-prd-scan -> /sp-prd-build` | `/sp-plan` | Grok projects install workflow skills under `.grok/skills` and keep root `AGENTS.md` as context. |
| Trae skills | `$sp-specify` | `$sp-prd-scan -> $sp-prd-build` | `$sp-plan` | Trae projects install workflow skills under `.trae/skills` and keep `.trae/rules/project_rules.md` as context. |
| Mistral Vibe skills | `/sp-specify` | `/sp-prd-scan -> /sp-prd-build` | `/sp-plan` | Vibe projects install workflow skills under `.vibe/skills`. |
| ZCode skills | `$sp-specify` | `$sp-prd-scan -> $sp-prd-build` | `$sp-plan` | ZCode projects install workflow skills under `.zcode/skills`; use `.agents/skills` only for cross-tool shared skills. |
| MiMo Code commands | `/sp.specify` | `/sp.prd-scan -> /sp.prd-build` | `/sp.plan` | MiMo projects install workflow commands under `.mimocode/commands` and keep root `AGENTS.md` as context. |
| Slash-dot command integrations | `/sp.specify` | `/sp.prd-scan -> /sp.prd-build` | `/sp.plan` | Gemini, Copilot, Windsurf, Forge, and similar command/prompt integrations use slash-dot examples unless their native UI documents a different launcher. |

`/sp-*` is not universal for skills-backed integrations. When these docs say to
run the canonical workflow `plan`, use the invocation form generated for your
selected integration, for example `$sp-plan` in Codex or `/skill:sp-plan` in
Kimi.

Skill map after `specify init`:

- Core workflow skills: `constitution`, `specify`, `plan`, `tasks`, `implement`, `review`, `accept`
- Support skills: `auto`, `ask`, `discussion`, `deep-research` (`research` alias), `test-design`, `design`, `fast`, `quick`, `checklist`, `analyze`, `debug`, `explain`, `implement-teams`, `prd-scan`, `prd-build`, `prd` (deprecated compatibility entrypoint), `map-scan`, `map-build`, `map-update`, `taskstoissues`
- Codex-only runtime: terminal `specify sp-teams` operations plus the generated `sp-teams` and `team` catalog entries

Conditional gates and follow-up commands:

- Generated projects query `specify-runtime cognition status --format json` and use the task-local `specify-runtime cognition compass` packet as the advisory project cognition index. Status and database files are runtime implementation details; agents do not read or write them directly.
- Generated workflows use `specify-runtime cognition compass --intent <intent> --query "$ARGUMENTS" --format json` as the default brownfield navigation intake and advisory navigation inputs. The packet returns readiness, `compass_state`, top-level `minimal_live_reads`, lane-level `first_pass_paths` with reasons, `coverage_diagnostics`, and `expansion_ref`.
- `specify-runtime cognition semantic-intake --input-json '<work-contract-input-json>' --format json` is the WorkContract v1 unified semantic candidate entrypoint for colloquial, localized, symptom-first, or mixed-language requests. Its input stays in memory rather than an agent-created file. It maps the agent's normalized facets to project-backed candidates, rejected false friends, permission hints, and learning hints; semantic-intake alone cannot authorize source changes, root-cause claims, fixed claims, complete claims, or release-safe claims.
- When semantic-intake escalation influences routing, workflows may record a v1.1 audit artifact as a replayable WorkContract artifact. `specify-runtime cognition semantic-audit --input-json '<semantic-audit-input-json>' --persist-dir <WORKFLOW_STATE_DIR> --format json` captures the semantic-intake input/output snapshot, selected/rejected basis, permission upgrade/downgrade reason, and action log, then atomically writes the registered input/output pair. Agents never recreate, submit, or patch either canonical audit file. The audit artifact does not authorize source changes or replace live-evidence verification.
- Persisted claim readiness is reusable only after resume validation. `specify-runtime cognition semantic-audit-resume --input-json '<resume-validation-json>' --format json`, when available, compares the CLI-persisted audit input/output pair against workflow state without a temporary validation file; it does not authorize source changes or final claims, and does not grant P3/P4. Multiple `authorized_claims` require a single `active_claim_type`, and failed, blocked, skipped, or inconclusive verification results keep claim readiness blocked with `verification_result_failed`, `verification_result_blocked`, or `verification_result_inconclusive` until a newer matching passed rerun supersedes them.
- Agents read top-level `minimal_live_reads` first, then lane-level `first_pass_paths` reasons and compact `claim_refs`. A claim's `route_confidence` is valid only within `confidence_scope=route_candidate`; `state`, `freshness`, and `stale` describe graph lifecycle, not current truth. Advanced `specify-runtime cognition query` returns bounded top-level `claim_signals`, and `specify-runtime cognition expand --section claim_evidence` returns bounded evidence refs with `source_path` and `span`. All require live verification and cannot prove current repository truth or final edit scope.
- Compass claim-aware ranking is a bounded rerank after repository-backed matching: `match_score` establishes candidate eligibility, while `claim_ranking.adjustment` is capped at `+1` for fresh supported or graph-generation-verified claims, `-1` for stale, and `-2` for contradicted. Claims cannot create candidates and cannot replace live verification. Selected lanes with `stale_claim_signal` or `contradicted_claim_signal` remain `usable_with_review` and return `reconcile_claims_with_minimal_live_reads` plus a lane-specific live repository action.
- When the compass packet is draft-like, localized, missing coverage, or needs explicit concept decisions, the advanced path remains `specify-runtime cognition lexicon --mode catalog` -> agent-authored `semantic_intake` and `concept_decisions` -> `specify-runtime cognition query --query-plan`. In short: `lexicon -> semantic_intake -> query`. The lexicon command exposes the alias catalog and candidate universe; facet coverage gates selection through `covered_facets`, `missing_facets`, `match_sources`, `lexicon_generation_id`, `candidate_universe_version`, and `active_generation_id`. Top lexical or vector similarity alone is not route truth. Map points, code proves: navigation terms are route vocabulary, not evidence by themselves. CJK or mixed CJK/ASCII prompts still require agent-owned translation when using the advanced path. The advanced CLI tool's `agent_normalization` field remains agent semantic guidance, not a route decision. `templates/project-map/**` remains a historical compatibility/export surface for handbook generation, but new workflows should not read or require `.specify/project-map/**`.
- Precision `query` is exact-binding only: raw or rewritten natural-language text belongs to Compass/semantic intake. Agents page the catalog through `catalog_page.next_offset`, select current `concept_id` values or exact paths, carry the matching `lexicon_generation_id`, and consume a query only when `resolution_state=resolved_exact`; binding failures are explicit rather than null results.
- Releases publish prebuilt `specify-runtime` binaries for Windows, Linux, and macOS. Human `specify init`/upgrade resolves a trusted binary, stores it in a content-addressed user cache, and hardlinks or copies it to `.specify/bin/specify-runtime` (`.exe` on Windows). Project config persists only that relative entrypoint and its digest. `SPECIFY_RUNTIME_BIN` and PATH are bootstrap/repair seeds only; they are never rendered into agent commands.
- All generated Classic `sp-*`, Advanced `spx-*`, and worker prompts use the same fixed workflow artifact boundary: `specify-runtime artifact show --path <project-relative-path> --view summary` for compact intake, explicit `--view full` expansion, and `artifact prepare` -> `artifact submit` for single-use leased writes. `specify-runtime artifact catalog` lists deterministic scaffold kinds, including `plan-contract` and `quick-status`; `specify-runtime artifact scaffold --kind <kind> --path <project-relative-path> --vars <compact-json>` creates registered boilerplate create-only for contracts, workflow state, design briefs, Plan's generic `research.md`, UI briefs, and Quick/Debug state, so agents fill semantic fields instead of reconstructing stable JSON or Markdown. The Deep Research package under `research/`, its `research-evidence/`, and derived `deep-research.md` are a narrower exception owned only by `specify-runtime deep-research`; generic artifact/evidence/result commands cannot write them. The runtime validates registered workflow paths, safe readiness defaults, and structured content before writing or atomically replacing a canonical artifact. Agents continue to edit task-scoped source and test files normally.
- Derived UI comparison reports use the narrower owner: `specify-runtime evidence visual-compare --feature-dir <feature-dir> --task-id <Txxx> --input-json '<observed-comparison-json>' --format json`. The agent supplies observed matrix/evidence facts; the runtime derives approved design/handoff bindings, exact coverage, tolerance, deviations, canonical path, and digest from `task-index.json`. Generic artifact mutation of these reports is rejected.
- See [Project Cognition Runtime](#project-cognition-runtime) for empty-project bootstrap behavior and brownfield first-baseline routing.
- Workflow-owned mutation closeout is planner-first and shared-runtime-owned: each source-changing `sp-*` workflow calls `cognition closeout-plan` with its registry-owned literal canonical id, receipt scope, `--scope-mode explicit`, and one `--changed-path` per owned path. The Agent fills only returned semantic/disposition/verification fields and executes `apply_argv`; it does not manually sequence update, validate-build, complete-refresh, and mutation-receipt. Shared `cognition closeout apply` rejects missing passing verification before mutation, runs the eligible deterministic tail, and records the bound receipt. `scope_result_state` describes this workflow's paths, while project-wide `result_state`, `global_freshness`, and `global_debt_reasons` preserve broader truth; `scope_ready` lets a successful current scope close without hiding unrelated project debt. `sp-map-update` remains the external/manual maintenance workflow for user edits, interrupted workflow repair, explicit map maintenance, and follow-up repair.
- The canonical implementation example is `specify-runtime cognition closeout-plan --workflow sp-implement --format json`; other mutation workflows substitute their own registry-owned literal canonical id and explicit receipt scope.
- The planner chooses `update_mode=delta_session` for leased delta capture or `update_mode=inline_json` for a bounded inline payload. Delta mode exposes `delta_append_draft.argv_prefix`; `update_argv` and other display-only command templates remain compatibility and diagnostic output, while the Agent executes the structured `apply_argv`.
- The Agent completes returned `unknown_path_dispositions`, `verification_evidence`, and `generated_surface_notes`. Missing or failed verification evidence stops the closeout before any mutation.
- The closeout result selects the finalization branch. Clean completion additionally requires `status=ok` and `readiness=query_ready`, a current bound `update_id`, and a matching receipt; otherwise the outcome stays partial or recorded-only without overstating project freshness.
- Closeout agents should use `known_unknowns` only for blockers that make the cognition update unsafe to trust. If unrelated dirty or untracked working-tree paths were excluded by explicit workflow-owned paths, record that as `confidence_notes` or `boundary.initial_dirty_paths`, not as blocking `known_unknowns`.
- Use `map-update` for localized stale cognition refresh recommendations, external/manual changed-path map maintenance, and ordinary existing-baseline gaps; use `map-scan` followed by `map-build` only for first/missing/unusable baseline, schema failure, schema v1 or old broad-schema rebuild-required readiness, zero active-generation `path_index` rows, missing or invalid `alias_index`, `explicit_rebuild_requested`, or `baseline_identity_invalid`.
- For the first brownfield cognition baseline, run `sp-map-scan` followed by `sp-map-build` when you want a map baseline. `build-from-scan` adapts the accepted legacy-compatible scan package into a versioned proposal and runs the deterministic cognition proposal compiler before SQLite publication; conflicts block before graph-store mutation. Compilation proves structural publication safety, not repository behavior, so compiled graph rows remain advisory route candidates. The pair is map-maintenance complete only when scan acceptance and build acceptance pass: `specify-runtime cognition validate-scan --format json` and `specify-runtime cognition validate-build --format json`. Ordinary workflows may continue from live repository evidence when the map is missing, stale, or blocked.
- `sp-map-scan` scan artifacts should emit canonical fields (`id`, `type`, `title`, `paths`, `source_id`, `target_id`, `attrs`, and coverage `rows`). The runtime accepts compatibility aliases such as `node_id`, `kind`, `label`, `source_node_id`, `target_node_id`, `attrs_json`, and coverage `coverage`, but `sp-map-build` creates `path_index` rows from `nodes[].paths`; `coverage.json` is coverage accounting, not a path-index source. Coverage or coverage-ledger rows do not prove a path was scanned unless a concrete scan packet assigned the path and that packet's worker result reported packet-local coverage.
- After a successful `sp-map-update`, committing the refreshed source changes does not require a full rebuild by itself. Its shared `apply_argv` owns validate-build, eligible complete-refresh, and the bound receipt. Preserve scope-level `partial_refresh`, `needs_rebuild`, `blocked`, and `recorded` without finalization; `scope_ready` is the distinct closeable state for a successful accepted scope with unrelated project debt. `record-refresh` remains compatibility-only.
- Recorded refresh and ready refresh are different outcomes: refresh commands may write update metadata, then still report `partial_refresh` when the shared freshness contract says runtime readiness remains blocked.
- Readiness diagnostics such as `recommended_next_action`, `needs_update`, and `needs_rebuild` remain available to explain map quality and suggested map-maintenance follow-up, but ordinary workflows must treat them as advisory and apply the map-update-first routing policy.
- Project cognition respects `.cognitionignore` at the repository root and `.specify/project-cognition/.cognitionignore`. The syntax is gitignore-compatible and applies to `map-scan`, `map-build`, and `map-update`; excluded paths must not enter project cognition graph evidence, runtime route indexes, or `minimal_live_reads`. `sp-map-scan` runs `specify-runtime cognition generate-ignore --format json` before inventory; when it returns `review_required=true`, review the command's returned `suggested_patterns` before continuing instead of opening runtime storage directly. A created starter with no suggestions returns `review_required=false` and needs no confirmation.
- `specify-runtime cognition scan-set --out .specify/project-cognition/tmp/scan-files.json --format json` resolves the temporary agent-facing candidate file list for scan workflows after the ignore gate is clear. Default stdout stays compact (`files` path plus `count`), and the handoff file contains only `files`; expanded exclusion detail belongs in explicit debug/explain flows.
- `scan-formats -> scan-policy-stage -> user confirmation -> scan-policy-confirm`
  creates a reusable cohort policy before `scan-prepare`. Known cohorts keep
  their confirmed decision across ordinary content/membership drift; new
  cohorts require review. Repeated preparation resumes an identical workbench
  or replays validated path-scope bundles whose source SHA-256, effective
  policy, and scan contract still match, then dispatches only invalidated
  scopes. `--full-rebuild` explicitly bypasses this cache. Repeating
  `build-from-scan` for the same validated receipt/compiler/schema fingerprint
  reuses the ready active generation and still proceeds through
  `validate-build`.
- When using another local directory as a reference, check whether that directory
  or its children contain `.specify/` before broad source reads. Run
  `specify-runtime cognition discover --root <path> --format json`; use reference cognition only
  when its response reports `reference_readiness=ready`, `freshness=fresh`, and
  `graph_ready=true`. Do not probe its status/database files. If the reference is
  blocked, stale, or incomplete, do not treat legacy
  `.specify/project-map/**` outputs as current truth; fall back to minimal live
  reads and recommend `map-update` for localized stale or weak reference
  coverage after a usable baseline. If the reference baseline is missing or
  unusable, recommend `map-scan -> map-build` only for first/missing/unusable
  baseline, schema failure, schema v1 or old broad-schema rebuild-required
  readiness, zero active-generation `path_index` rows, missing or invalid
  `alias_index`, `explicit_rebuild_requested`, or `baseline_identity_invalid`.
  Schema v5 is current-only. The current runtime does not migrate schema v4 or older databases. Never move, remove, archive, or replace `project-cognition.db` directly. Run `specify-runtime cognition archive-incompatible-store --inspect --format json`, execute its hash-guarded `archive_argv`, then run `sp-map-scan -> sp-map-build` with the current binary to publish schema v5 with revisioned typed graph-claim lifecycle and reconciliation tables.
- Support drift is not runtime-truth staleness. When `freshness` is `support_drift`, resolve or ignore the support-surface change instead of reflexively routing to `map-update`.
- Map points, code proves: technical claims must be backed by live code, tests, scripts, configuration, or authoritative docs.
- Planning-only workflows do not acquire source mutation authority: `specify`, `deep-research`, `plan`, `test-design`, and `tasks` write their owned planning artifacts only. If a request requires source/runtime/template/config/test/generated-asset changes, they must hand off to a registry-owned mutation workflow and stop; they do not conditionally run mutation closeout themselves. The receiving mutation owner applies its rendered planner-first project cognition closeout, while `sp-map-update` remains the external/manual maintenance workflow for user edits, interrupted workflow repair, explicit map maintenance, and follow-up repair.
- `auto` to resume the recommended next workflow step from current repository state; for feature stages it reads `workflow.json` through `specify-runtime workflow show` then `specify-runtime workflow next` and consumes structured `next_argv` before consulting rich `workflow-state.md`, `implement-tracker.md`, quick-task `STATUS.md`, or debug session files. It continues under the routed workflow's contract without rewriting downstream state to `sp-auto`. When the routed workflow would only ask a bounded question or confirmation with one safe recommended/default answer, `auto` accepts that recommendation and continues; when it cannot do so safely, it reports the blocker plus a self-unblock recommendation instead of waiting silently.
- inside a managed Run, `auto` routes only the current Run subject and verifies `SPECIFY_RUN_WORKSPACE`; an unbound read-only invocation stops when more than one safe candidate remains instead of guessing from branch recency
- `ask` for read-only evidence-backed project Q&A. Use it when you need a direct answer from project files, templates, docs, state, or memory before choosing an action workflow. Project cognition guides the search; live evidence proves the answer. Same-topic follow-ups reuse the prior evidence set when it still applies, localized or project-slang terms are normalized into project vocabulary, and complex answers separate proven facts from evidence-derived inferences. `sp-ask` is independent from `sp-discussion`; it creates no ask state or handoff, makes no source edits, and does not run tests, builds, package managers, or project CLI commands by default. Do not teach a `specify ask` helper in v1.
- `discussion` to shape a rough idea before formal specification or direct quick delivery. At handoff it presents both paths and their eligibility, explains any blocker, recommends one eligible path from delivery complexity and consequence profile, and leaves the final choice to the user. It favors Quick for bounded, well-understood work and Specify for high ambiguity/complexity, interacting systems, architecture/data migration/security/compliance/rollout concerns, broad acceptance obligations, or durable specification traceability; size alone is not a hard routing ceiling. Only after that choice does it submit the confirmed semantic contract through `specify-runtime discussion write-handoff`; the runtime materializes the single machine-oriented `handoff-to-specify.json`. When the contract introduces no quick-stage `semantic_delta`, Quick binds understanding to the confirmed `review_digest` and does not ask for the same confirmation again.
- `prd-scan` followed by `prd-build` reverse-extracts a repository-first current-state PRD reconstruction archive from an existing project. Substantive `prd-scan` runs are subagent-mandatory; workers inspect implementation reality, docs, tests, routes, UI/API surfaces, project cognition evidence, and memory, while `specify-runtime prd-scan`, `specify-runtime prd-build`, and the artifact/evidence CLIs alone materialize `.specify/prd-runs/<run-id>/`. The ten growing scan ledger/contract JSON files use `prd-scan record-upsert|record-remove|record-show|record-list`, so agents send or inspect one semantic row while the Go runtime owns each envelope, ordering, optimistic digest, and atomic write. `prd-build scaffold` then expands all missing master/export boilerplate from installed templates in one transaction; agents patch only semantic sections and never reconstruct or replace those large documents. Critical reconstruction claims target `L4 Reconstruction-Ready`, and `config-contracts.json` is part of the scan contract surface. `prd-build` compiles from the scan package into the expanded archive, including config/protocol/state/error/verification/risk exports. The exported suite includes `exports/README.md` as the package navigation entry and `exports/prd.md` as the main reader-facing PRD, and `prd-build` must not perform a second repository scan. `prd` remains a deprecated compatibility entrypoint that should route into the same pair.
- `specify` also owns focused repair of an existing spec when analysis, references, or gaps need more work before planning
- `deep-research` is the conditional pre-Plan feasibility gate for clear requirements whose implementation chain is still unproven. The runtime binds the exact source spec/capabilities, coordinates bounded research workers, validates repository/external/spike provenance, records leader acceptance or rejection with one bounded retry, closes capability-to-handoff-to-evidence coverage, requires an independent audit, and publishes a revision/hash-bound `Planning Handoff` that `plan` verifies. It does not own requirement discovery, final architecture design, executable tests, or production implementation. Skip it for minor changes to already-proven behavior; `research` is only a compatibility alias and creates no separate artifacts
- `checklist` to generate requirement-quality checklists after planning so the written requirements can be audited before implementation
- `analyze` is an optional read-only diagnostic and legacy revalidation pass once `tasks.md` exists; run the cross-artifact consistency pass across `spec.md`, `context.md`, `plan.md`, and `tasks.md` only when explicitly requested or recorded by existing state
- `debug` to investigate blocked implementation work, regressions, or execution-time defects without reopening upstream planning artifacts unless drift is discovered. It now defaults to project-cognition-backed minimum intake; the heavier Stage 1A/1B observer-contract flow is reserved for missing/ambiguous/stale map coverage, competing truth owners, or failed verification loops.
- `explain` to describe the current spec, plan, task, implement, project cognition, or compatibility/export artifact in plain language
- `specify-runtime result show -> specify-runtime candidate build -> candidate review -> accept receipt -> cas publish`, followed separately by `sync safe`, for immutable multi-Run delivery with explicit human acceptance and target-ref compare-and-swap protection
- `integration repair` to refresh generated shared/runtime-managed assets after CLI upgrades or when `specify check` reports stale launcher, script, or hook surfaces
- when you run `analyze` and it finds upstream issues, it becomes a workflow gate, not a dead-end audit: reopen the highest invalid stage and regenerate downstream artifacts before continuing implementation
- `analyze` now also detects boundary guardrail drift through stable issue codes: `BG1` (missing `Implementation Constitution`), `BG2` (missing task guardrails), and `BG3` (missing implementation-time boundary confirmation)
- `analyze` should also surface delegated-execution packet gaps through `DP1` (missing compiled hard rules), `DP2` (missing required references or forbidden drift), and `DP3` (missing subagent validation evidence)
- `implement` owns event-triggered review for clean task packages. It validates the entry revision, then reviews drift, parallel joins, write-scope changes, validation failures, worker concerns, obligation conflicts, real-entrypoint gaps, and review-window limits. One task lifecycle record carries result, validation, review verdict, blockers, and recovery; upstream truth changes still route to the owning phase.

Already have code? Query `specify-runtime cognition status --format json` and use `specify-runtime cognition compass --intent <intent> --query "$ARGUMENTS" --format json` as the default brownfield navigation intake and advisory navigation inputs. The packet returns readiness, `compass_state`, top-level `minimal_live_reads`, lane-level `first_pass_paths` with reasons, `coverage_diagnostics`, and `expansion_ref`. Read top-level `minimal_live_reads` first, then use lane-level `first_pass_paths` reasons and `before_fix_claim` checks to prove or reject the route from live repository evidence; these paths are first evidence, not final edit scope. When the compass packet is draft-like, localized, missing coverage, or needs explicit concept decisions, the advanced path remains `specify-runtime cognition lexicon --mode catalog` -> agent-authored `semantic_intake` and `concept_decisions` -> `specify-runtime cognition query --query-plan` (`lexicon -> semantic_intake -> query`). The current query contract is `claim_retrieval_contract_version=2` and `candidate_universe_version=2`; carry the latter from lexicon into every explicit query plan. Never parse missing or non-current versions as legacy input; rerun lexicon or compass with the current binary and repair the install if needed. When a full first brownfield cognition baseline is intentionally needed or map maintenance is chosen, run `sp-map-scan` followed by `sp-map-build` and require `specify-runtime cognition validate-scan --format json` plus `specify-runtime cognition validate-build --format json` to pass for that map-maintenance workflow. Ordinary workflows may continue from live repository evidence when the map is missing, stale, or blocked. Schema v5 is current-only: the runtime does not migrate schema v4 or older databases. Never move, remove, archive, or replace the store directly; run `specify-runtime cognition archive-incompatible-store --inspect --format json` and execute its hash-guarded `archive_argv` before `sp-map-scan -> sp-map-build`. After that, source-changing `sp-*` workflows run planner-first project cognition update for their own changed paths and affected surfaces during closeout. Use `map-update` for external/manual localized stale cognition maintenance and ordinary existing-baseline gaps. Use map-scan -> map-build only for first/missing/unusable baseline, schema failure, an older schema or old broad-schema rebuild-required readiness, zero active-generation path_index rows, missing or invalid alias_index, `explicit_rebuild_requested`, or `baseline_identity_invalid`.
Generated projects expose cognition freshness through `specify-runtime cognition status --format json`, so brownfield workflows can decide whether the current cognition baseline is `fresh`, `missing`, `stale`, `support_drift`, `partial_refresh`, or `possibly_stale` before proceeding without parsing runtime storage. Ordinary `sp-*` workflows treat cognition freshness as advisory navigation, continue with live repository evidence, and apply the map-update-first routing policy while using `recommended_next_action` for public state guidance.

## Senior Consequence Analysis Gate

Project cognition is necessary but not sufficient for dependency analysis. It gives workflow agents ownership, consumers, state surfaces, change-propagation facts, verification routes, conflicts, and known unknowns. `sp-map-build` and the project cognition runtime provide the evidence layer, but the Senior Consequence Analysis Gate turns those facts into product and implementation obligations.

When work involves lifecycle operations, running or concurrent objects, destructive actions, shared state, downstream consumers, compatibility, security, or multiple plausible behaviors, workflows must preserve:

- Affected Object Map
- State-Behavior Matrix
- Dependency Impact Table
- Recovery And Validation Contract
- Coverage Gaps

For example, "close team" must consider running workers, queued tasks, late result submission, heartbeat state, `status`, `await`, `resume`, `cleanup`, idempotency, and validation evidence before the workflow can claim the feature is ready for the next stage.

Use `CA-###` IDs for consequence obligations that must survive handoff from `discussion` to `specify`, `plan`, `tasks`, `implement`, and `quick`; `analyze` consumes the same obligations only when run as an optional diagnostic or legacy revalidation pass. `fast` upgrades when the gate triggers; `quick` tracks consequences and acceptance locally instead of handing off solely because the task is large or consequence-heavy; `debug` traces the dependency loop and rejects surface-only fixes.

Routing guide for direct delivery work:

- `sp-quick` and `sp-debug` first assess only evidence already present in the
  current conversation context, without a tool call. When that evidence names
  the exact owner, consumers, risk boundary, and verification surface—and, for
  Debug, proves the failure mechanism—the agent recommends a **context-direct**
  change/fix and lets the user choose it or the full workflow. Insufficient
  evidence shows no menu and enters the full Quick or full Debug path. Large,
  cross-cutting, multi-item, or resumable work always uses full Quick; an
  unproven or competing root cause always uses full Debug. Context-direct skips
  entry Learning and Project Cognition navigation plus Quick/Debug state setup,
  but it keeps RED/reproduction, fresh verification, diff review, external
  effect gates, and exact-changed-path Project Cognition closeout.
- `sp-fast` is only for trivial local fixes. Stay on that path only when the change is obvious, touches at most 3 files, and does not touch a shared surface. It still runs consume-only Learning intake, Project Cognition navigation, RED-first execution when behavior changes, targeted verification, and a same-leader Lightweight Review; it creates no worker packet or subagent lane.
- Move from `sp-fast` to `sp-quick` as soon as the work expands to more than 3 files, touches a shared surface, or needs research or clarification.
- `sp-quick` / `spx-quick` is a resumable direct-delivery workflow, not a small-task-only lane. Use it when the desired outcome is clear enough to implement directly, even if the work spans multiple capabilities, architecture or migration choices, compatibility constraints, rollout coordination, or acceptance-heavy validation.
- Quick may use task-local planning, multiple lanes or batches, consequence and acceptance tracking, and validation to preserve control over larger work. Task size, multi-capability scope, or consequence breadth alone must not force a handoff to `sp-specify` / `spx-specify`.
- `sp-specify` / `spx-specify` remains a separate formal specification path chosen explicitly for requirements-first work, not an automatic upgrade from Quick.
- The full `sp-quick` branch performs one runtime-owned Decision Checkpoint before substantive execution. Stage it with `specify-runtime quick checkpoint-stage`, bind approval with `checkpoint-confirm`, and render `decision` / `delivery` / `pulse` views with `checkpoint-show`. The Decision Checkpoint asks the user to confirm goal, visible result, scope, stable `Q1`/`Q2` deliverables and product-level dependencies, independent acceptance for every work item, recommended approach, assumptions/risks, overall completion evidence, and reconfirmation trigger. Delivery Map waves, subagents, file splits, and test order remain agent-owned and never enter `confirmation_digest`. Discussion handoffs with no semantic delta inherit confirmation and skip re-approval. For applicable UI work, an independent UI Confirmation proposal is staged with the decision and one reply confirms both. When Quick adopts a registered design, exact `decision.ui_confirmation.design_binding` is part of that confirmation digest; the later top-level STATUS adoption copy must match it. Freeform prose or bullet-only confirmations do not satisfy this gate.
- `sp-fast` first runs `specify-runtime learning start --command fast --format json` with `consume-only` policy, then `sp-fast` and the full `sp-quick` branch pass the project cognition gate: run `specify-runtime cognition compass --intent implement --query "$ARGUMENTS" --format json` as the default brownfield navigation intake. The explicit user-selected context-direct branch is the only Quick entry exception; it relies on the evidence listed in the choice and still performs exact-path mutation closeout after changes. Continue full-flow intake from the returned readiness, `compass_state`, top-level `minimal_live_reads`, lane-level `first_pass_paths` with reasons, `coverage_diagnostics`, and `expansion_ref`; read top-level `minimal_live_reads` first, then use lane-level `first_pass_paths` reasons and `before_fix_claim` checks to prove or reject the route from live repository evidence. These paths are first evidence, not final edit scope. When the compass packet is draft-like, localized, missing coverage, or needs explicit concept decisions, use the advanced `specify-runtime cognition lexicon --mode catalog` -> agent-authored `semantic_intake` and `concept_decisions` -> `specify-runtime cognition query --query-plan` path (`lexicon -> semantic_intake -> query`). Generated agent commands always use the relative project runtime entrypoint; user-scoped environment variables and PATH participate only in human bootstrap or repair.
- Pass the planned object as one structured argv value to `specify-runtime cognition query --intent <intent> --query-plan '<inline-json>' --format json`; use the integration's native argument API when shell quoting is brittle, and never create a query-plan file. `path_hints`/`reason` are accepted aliases for `paths`/`selection_reason`.
- If the work is a bug fix or regression and the root cause is still unknown, use `sp-debug` instead of treating `sp-quick` as a symptom-fix lane.
- The full `sp-debug` branch performs one Debug Understanding Checkpoint before substantive investigation. The fixed plain-text Debug table asks the reporter to confirm the problem, expected behavior, occurrence conditions, investigation boundary, fix authority, assumptions to correct, and reconfirmation trigger; hypotheses and evidence sequencing remain agent-owned. For applicable UI symptoms, an independent UI Confirmation target baseline follows the main table without pre-approving a repair, and one reply confirms both. Checkpoint cards must not use HTML tags or inline line-break markup in terminal output.
- `sp-debug` is complexity-based: small focused investigations may run leader-inline, while broad or independent evidence lanes use one or more subagents. Unsafe or unavailable dispatch remains `subagent-blocked` with `execution_surface: none`.
- Behavior-changing work across `sp-fast`, `sp-quick`, `sp-implement`, and `sp-debug` follows a failing test first rule. Capture a RED state before production edits; if the touched area lacks a viable automated test surface, add the smallest safe bootstrap in the owning workflow. `sp-fast` may route that work to `sp-quick`; Quick treats the harness as an ordered lane or batch rather than escalating to `sp-specify`.
- UI/TUI/CLI/API/runtime-visible implementation tasks generated by `sp-tasks` should carry real-entrypoint evidence requirements. Component, reducer, helper, or hand-built state tests can support the change, but `sp-implement` must reject synthetic-only consumer proof when `required_evidence` includes `real_entrypoint_evidence`.
- Quick workspaces now live under `.planning/quick/<id>-<slug>/`, with `STATUS.md` as the task source of truth, an ordered work-item/dependency/acceptance ledger for one or many deliverables, and `.planning/quick/index.json` as a derived management index.
- Invoking `sp-quick` with no arguments should resume unfinished quick work when possible. If only one unfinished quick task exists, continue it automatically. `blocked` quick tasks still count as resumable unfinished work.
- Use the project-local `specify-runtime quick list` to inspect unfinished quick tasks by default.
- Quick-task helper command shapes:
  - Command shape: `specify-runtime quick status <id>`
  - Command shape: `specify-runtime quick resume <id>`
  - Command shape: `specify-runtime quick close <id> resolved|blocked` (positional status)
  - Source-changing work requires `specify-runtime quick cognition-closeout <id> --result-state ready|no_op|mark-dirty|partial --reason "…"` before resolved close; `quick status` exposes `cognition_closeout`
  - Command shape: `specify-runtime quick archive <id>`
- Discussion sessions live under `.specify/discussions/<slug>/`. `discussion-state.json` is canonical typed state, `discussion-state.md` is a short derived compatibility view, `discussion-log.jsonl` stores compact semantic checkpoints, and `.specify/discussions/index.json` is a derived management index. The routing gate shows both eligible consumers and a complexity-informed recommendation; the user-selected consumer is then recorded in `recommended_consumer` and protected by `review_digest`. `handoff-ready` remains resumable until that consumer produces bound evidence. `sp-quick` consumes a direct-delivery contract into task-local `STATUS.md`; `sp-specify` consumes a formal spec-first contract before feature creation. After verified consumption, `specify-runtime discussion mark-consumed <slug> --feature-dir <consumer-workspace>` closes the source discussion so stale handoffs cannot block future `sp-auto` routing; `--feature-dir` is the compatibility spelling and accepts a Quick workspace.
- Use `specify-runtime discussion list` to inspect unclosed discussions by default.
- Discussion helper command shapes:
  - Command shape: `specify-runtime discussion init <topic> [--slug <slug>]`
  - Command shape: `specify-runtime discussion status <slug>`
  - Command shape: `specify-runtime discussion resume <slug>`
  - Command shape: `specify-runtime discussion checkpoint <slug> --input-json '<object|@path|->' [--summary <summary>] [--phase <phase>] [--user-goal <goal>]`; persists accepted turn_packet semantic fields and rejects unknown fields
  - Command shape: `specify-runtime discussion write-handoff <slug> --input-json '<draft-json|@path|->'`; schema via `api schema discussion-write-handoff-input`
  - Command shape: `specify-runtime discussion bind-consumer <slug> --feature-dir <feature-dir> --input-json '<transition-json|@path|->'`; the runtime validates the ready contract and materializes the feature compatibility pointer
  - PowerShell note: prefer `--input-json @payload.json` or stdin `-` because inline quoting often strips double quotes
  - Command shape: `specify-runtime discussion validate-handoff <slug> --mode draft|ready`
  - Command shape: `specify-runtime discussion confirm-handoff <slug> --digest <review-digest>`
  - Command shape: `specify-runtime discussion mark-ready <slug>`
  - Command shape: `specify-runtime discussion close <slug> --status completed|abandoned`
  - Command shape: `specify-runtime discussion mark-consumed <slug> --feature-dir <feature-dir>`
  - Command shape: `specify-runtime discussion archive <slug>`
- Move from `sp-quick` / `spx-quick` to `sp-specify` / `spx-specify` only when the user explicitly chooses the formal specification path. If requirements, boundaries, order, dependencies, or acceptance truth are unclear, Quick pauses at its checkpoint or amendment and resolves that decision in place; it does not transfer automatically. Do not route away from Quick merely because the request spans multiple capabilities, carries compatibility or rollout risk, or needs substantial validation.

Required action markers:

- `[AGENT]` marks a required AI action and is independent from `[P]`.
- `[P]` still means parallel-safe work; `[AGENT]` does not imply parallelism, subagent dispatch, or runtime routing by itself.
- Existing `AGENTS.md` files are extended through a managed `SPEC-KIT` block instead of full-file append or replacement.
- First-wave `[AGENT]` coverage started with `sp-fast`, `sp-quick`, `sp-map-scan`, and `sp-map-build`; the shared `specify`, `plan`, `tasks`, `implement`, and `debug` workflows now use the same marker for hard gates and required state updates.

Project Learning lifecycle:

- Agents consume Learning only through the CLI. Storage paths under `.specify/memory/learnings/` and `.planning/learnings/` are runtime-private implementation details, not normal agent-access surfaces.
- Consumption is progressive and read-only: `learning start` returns task-relevant summary cards, `learning list` filters or pages compact summaries, and `learning show` expands exactly one selected record.
- A summary card carries `ref`, sanitized summary, recommended action, type, status, signal, occurrences, applicability, canonical `trigger_signals`, `show_argv`, and optional safety fields. Start/list/show may also expose an optional `assessment` containing `learning_value` (`tier` and reason codes), `content_safety` (`sensitivity`, risk tier, and redaction labels), and a sanitized decision/reason. Old records without `assessment` remain valid.
- Production remains explicit: `capture` and `capture-auto` create or merge every reusable candidate; `promote` first confirms a learning and only then explicitly promotes a stable recurring learning into project rules. Reading never auto-promotes.
- `learning start` protects mature knowledge with a 15-card stable quota and a bounded candidate slot of up to 5 cards; either class fills unused capacity. Candidate slots rank context, assessed value, recurrence, and novelty, and diversify repeated type/source/recurrence families when enough candidates exist. This bound controls disclosure, not candidate storage.
- Trigger review covers user corrections, repeated attempts, route changes, blockers/recovery, false leads, decisive signals, hidden dependencies, validation gaps, tooling traps, state loss, cognition gaps, reusable constraints, and near misses. Routine output and one-off facts are skipped.
- Owning workflows record explicit semantic signals in `workflow-state.md` under `## Learning Triggers` as `kind: compact evidence`; `capture-auto` deterministically maps canonical kinds to Learning types and agent guidance. Summary, `trigger_signals`, and evidence are sanitized agent-facing projections; raw sensitive values never enter Learning storage, registry, or read API payloads. Learning value and sensitivity are assessed independently: reusable sensitive lessons become `capture-sanitized`, and only high-value evidence that loses all reusable meaning after sanitization is deferred. Sensitivity alone never causes `ignore`.
- Canonical redaction labels include `credential`, `email`, `private_key`, `machine_path`, `personal_identifier`, `business_identifier`, and `organization_sensitive`; new replacements are `[REDACTED_PHONE]`, `[REDACTED_BUSINESS_ID]`, and `[REDACTED_ORG_TERM]`. Optional literal detector lists and `deferred_review_days` live under `.specify/config.json.project_learning` and are validated by `project-learning-policy-schema.json`; each list allows at most 64 distinct 1..128-character literals, review days range from 1 to 365, and arbitrary regex detectors are not supported. Invalid policy emits `project_learning_policy_invalid:using_builtin_policy` while safe reads use built-in protection; mutation or assessment commands, including dry-run, fail closed.
- Classic commands use the shared Learning partial/passive skill. Every SPX skill receives the independent Advanced `project-learning.md` reference; both profiles share one Classic command namespace in the runtime.
- Agent runtime surfaces:
- `specify-runtime learning start`
  - Command shape: `specify-runtime learning start --command <workflow> --format json`
- `specify-runtime learning list`
  - Command shape: `specify-runtime learning list --command <workflow> --query "<signal>" --format json`
  - Use `--all` for the complete matching summary catalog; otherwise follow `pagination.next_argv`.
- `specify-runtime learning show`
  - Command shape: `specify-runtime learning show --ref <recurrence-key-or-id> --format json`
- `specify-runtime learning capture`
  - Required options: `--command`, `--type`, `--summary`, `--evidence`
  - Agent guidance fields: `--problem`, `--action`, `--trigger`, `--success`, `--avoid`, and `--exception`
- `specify-runtime learning capture-auto`
  - Command shape: `specify-runtime learning capture-auto --command <workflow> (--feature-dir <dir> | --workspace <dir> | --session-file <file>) --format json`
  - Add `--dry-run` to return the sanitized assessment without writing a candidate, registry, review state, or metric.
- `specify-runtime learning review`
  - Command shape: `specify-runtime learning review --command <workflow> --decision none|captured|auto-captured|deferred|manual-capture-needed [--rationale "<reason>"] [--recurrence-key <key>] --format json`
  - `deferred` and `manual-capture-needed` require rationale and remain pending until a matching durable candidate, confirmed learning, or project rule exists. Captured decisions succeed only after that match is verified; `none` is blocked while matching deferred/manual work remains pending.
- `specify-runtime learning status`
  - Command shape: `specify-runtime learning status [--command <workflow>] --format json`
  - Read-only aggregate pending/due/age buckets only; no evidence, rationale, Learning refs, recurrence keys, or timestamps.
- `specify-runtime learning metrics`
  - Command shape: `specify-runtime learning metrics [--command <workflow>] --format json`
  - Read-only aggregate totals, decisions, value/risk tiers, reason/label counts, and derived confirmation rate plus age buckets computed in memory from review state. Age buckets are not persisted, and reads do not increment counters or advance state. Persistent counters conform to `project-learning-metrics-schema.json` and contain no evidence, summaries, rationale, refs, paths, or timestamps.
- `specify-runtime implement closeout`
  - Command shape: `specify-runtime implement closeout --feature-dir <feature-dir> --format json`
  - Uses `git diff --stat` and `git diff --name-status` as part of the recorded implementation baseline. Writes `FEATURE_DIR/implementation-summary.md` plus `FEATURE_DIR/implementation-handoff.json` and hands off to `sp-review` / `spx-review`; the JSON response exposes these as `implementation_summary` and `implementation_handoff`, and it does not prepare human acceptance. Review closeout refreshes the summary, prepares fingerprinted `FEATURE_DIR/human-acceptance.json`, and hands off to `sp-accept` / `spx-accept`.
- `specify-runtime accept prepare|validate|closeout`
  - Command shape: `specify-runtime accept prepare --feature-dir <feature-dir> --format json`
  - Prepares or freshness-checks the resumable acceptance state, validates its scenarios/cursor/verdict, and closes only a fresh explicit human acceptance.
- `specify-runtime learning promote`
  - Command shape: `specify-runtime learning promote --recurrence-key <key> --target learning|rule`
- Human compatibility/maintenance commands `specify learning ensure|status|aggregate` remain on the bootstrap/operator CLI; they are distinct from the runtime-owned agent `learning status` and `learning metrics` surfaces.
- Learning remains a passive lifecycle rather than a new daily `sp-*` workflow. `fast` and read-only/orchestrator workflows consume without capture; other non-trivial workflows consume before deeper work and capture at owning closeout only when a reusable signal exists.
- Durable eval helpers turn promoted rules into local regression checks:
  - `specify eval create`
    - Command shape: `specify eval create --recurrence-key <key> --summary "<summary>"`
  - `specify eval status --format json`
  - `specify eval run --format json`
- Use `specify eval create` after a rule or learning becomes stable enough that the repository should keep proving it, not just remember it.

First-party hook runtime:

- Runtime-owned workflow validation lives in the project-local Go binary: `specify-runtime hook validate-state|validate-artifacts|validate-commit`. Stage closeout calls the same Go validators in-process; it never launches Python.
- PRD lifecycle state is Go-owned as well: `specify prd*` and the retained Bash/PowerShell PRD wrappers delegate to `specify-runtime prd-scan|prd-build`. The packaged `scripts/shared/prd-state.py` file is legacy compatibility data only and is not an active workflow path.
- `specify hook ...` remains only for compatibility, operator diagnostics, and native-adapter capabilities that have not moved into the Go runtime, such as prompt/read guards and session presentation. Normal `sp-*` workflow steps should not call `specify hook ...`; they use the project-local Go runtime.
- Important diagnostic command shapes:
  - `specify-runtime hook validate-state --command <workflow> --feature-dir <dir>`
  - `specify-runtime hook validate-artifacts --command <workflow> --feature-dir <dir>`
  - `specify-runtime hook validate-commit --commit-message "<message>"`
  - `specify hook validate-session-state --command <workflow> --feature-dir <dir>`
  - `specify hook validate-packet --packet-file <path>`
  - Normal result validation/submission uses `specify-runtime implement result-merge --result-json '<inline-json>'` or `specify-runtime result submit ... --result-json '<inline-json>'`; the legacy file-only hook remains diagnostic compatibility and is not a generated workflow step.
  - `specify hook validate-read-path --target-path <path>`
  - `specify hook validate-prompt --prompt-text "<text>"`
- Project cognition freshness should use the public specify-runtime cognition commands:
  - Command shape: `specify-runtime cognition changes --format json`
    - Git-native change plan for `sp-map-update`; reports `summary.included`, `summary.ignored`, `summary.known`, `summary.unknown`, `ignored_paths`, `unknown_paths`, top-level `next_action`, and per-change `recommended_action` before incremental update recording.
  - Command shape: `specify-runtime cognition validate-build --format json`
  - Command shape: `specify-runtime cognition complete-refresh --format json` (only after the matching latest-update validation receipt exists)
  - Command shape: `specify-runtime cognition mark-dirty --reason "<reason>" [--origin-command <workflow>] [--origin-feature-dir <dir>] [--origin-lane-id <lane-id>] [--packet-file <packet-json>]`
  - Historical compatibility/export surface: legacy project-map artifacts may still exist in old projects, but there is no Python runtime alias and new generated workflow guidance should not call them.

Claude Code integration note:

- `specify init --ai claude` installs thin native adapters in `.claude/hooks/` and merges project-local `.claude/settings.json`.
- Managed Claude hook entries use a single shell-free `node -e ... claude <route>` command. The inline launcher walks upward from the hook working directory to find `.specify/bin/specify-hook.mjs`, so hooks still work when Claude runs from a monorepo subdirectory such as `apps/web`, then the shared Node launcher resolves project-local runtime details from the hook payload and project files.
- The current managed Claude native hook set covers:
  - `SessionStart` statusline/orientation context plus bounded compaction-backed resume cues
  - `UserPromptSubmit` prompt-guard checks plus shared workflow-policy enforcement
  - `PreToolUse` shared workflow-policy checks, read-boundary checks, and inline commit-message validation
  - `PostToolUse` session-state drift warnings for active implement/quick/debug flows, plus soft learning-signal warnings and compaction refresh guidance when workflow state records reusable friction
  - `Stop` context-monitor checkpoint blocking or advisory output before stop, plus compaction-backed resume cues and soft learning-signal warnings when active workflow state crosses the pain threshold
- These adapters are intentionally thin: runtime-owned validation routes only to the project-pinned `specify-runtime`; remaining host-event checks use the compatibility hook adapter without duplicating workflow truth in standalone scripts.

Codex/OMX integration note:

- The OMX runtime manages Codex native hooks through `.codex/hooks.json` and `codex-native-hook.js`.
- The managed Codex native hook set covers `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, and `Stop`.
- `SessionStart` and `Stop` can append bounded compaction-backed resume cues from the shared hook surface.
- `UserPromptSubmit` can bridge shared workflow-policy blocking when the active workflow is being asked to jump phases unsafely.
- `PostToolUse` and `Stop` bridge shared learning-signal warnings when active workflow state records reusable friction.
- Learning capture and terminal learning review remain direct learning-memory responsibilities; native hooks may surface soft signals, but normal `sp-*` workflow steps should not call hook learning commands.

Gemini integration note:

- `specify init --ai gemini` installs thin native adapters in `.gemini/hooks/` and merges project-local `.gemini/settings.json`.
- The managed Gemini native hook set covers `SessionStart`, `BeforeAgent`, and `BeforeTool`.
- `SessionStart` can append bounded compaction-backed resume cues from the shared hook surface.
- `BeforeAgent` applies shared prompt guards, targeted workflow-policy checks for explicit phase jumps, and soft learning-signal warnings when active workflow state records reusable friction.
- `BeforeTool` applies shared read-boundary and inline commit-message validation.
- As with Claude and Codex, learning capture and terminal learning review remain direct learning-memory responsibilities; native hooks may surface soft signals, but normal `sp-*` workflow steps should not call hook learning commands.

Native hook coverage matrix:

| Surface | Shared `specify hook ...` | Native adapter/runtime | Learning signal bridge | Native terminal review gate |
| --- | --- | --- | --- | --- |
| Claude | Yes | Yes | Yes | No |
| Codex/OMX | Yes | Yes | Yes | No |
| Gemini | Yes | Yes | Yes | No |
| Other integrations | Yes | No | No | No |

Formal delivery flow:

```text
specify -> [deep-research when feasibility is unproven] -> plan -> [test-design] -> tasks -> implement -> review -> accept
```

`specify` also repairs an unclear existing specification. `design` is a separate UI
contract lane that feeds `specify` or `quick`; it is not an unconditional
stage in this sequence.

`test-design` is an independent producer and planning-only quality lane; it
does not require a completed Plan. Its leader freezes the scope, uses Project
Cognition only for navigation, verifies facts against current code, tests,
configuration, official contracts, and live evidence, coordinates bounded
read-only subagents, and joins an independent audit. The runtime publishes the
content-addressed package and builds typed pointer-only projections for Plan,
Quick, Tasks, and Review. Those consumers verify and read them without changing
canonical Test Design. Implement consumes only the verified task-packet
TC/TD subset, and Review treats Test Design as an oracle rather than PASS
evidence. The default formal path remains `plan -> [optional test-design] ->
tasks`; executable tests and fixtures remain owned by `tasks -> implement`.

`plan` and `tasks` use adaptive execution: `execution_model: adaptive`, `execution_mode: light | standard | heavy`, and `dispatch_shape: leader-inline | one-subagent | parallel-subagents | subagent-blocked`. Light, low-risk single-lane planning or task generation runs leader-inline. Standard work uses native subagents when available; if native subagents are unavailable and no high-risk trigger is present, it may continue leader-inline with `capability_degraded: true`. Standard work that has no safe subagent lane or cannot be packetized safely records `dispatch_shape: subagent-blocked` and stops. Heavy or safety-critical work also blocks when native subagents are unavailable or the work is unpacketizable. Managed-team fallback is not part of adaptive plan/tasks dispatch.

Closed-loop remediation after `tasks`:

- If the defect is in `spec.md` or `context.md`, go back to `specify`, then rerun `plan`, `tasks`, and `implement` after the upstream artifacts are repaired.
- If the defect is in `plan.md`, go back to `plan`, then rerun `tasks` and `implement`.
- If the defect is only in `tasks.md`, rerun `tasks`, then resume `implement`.
- `tasks` should run an implementation-readiness self-audit before final handoff, covering task coverage, locked decision preservation, task guardrails, DP1/DP2/DP3 readiness, reference fidelity mapping, unmapped tasks, and write-set conflicts.
- If `analyze` is run, it should finish a complete blocker bundle before selecting the single recommended next command; do not treat one discovered blocker as permission to stop the rest of the analysis pass.
- repeated `tasks -> analyze -> tasks` loops are abnormal. only use `analyze` again when explicitly required by legacy or diagnostic state; if revalidation finds new task-layer blockers that were detectable before remediation, diagnose a previous analyze miss or a tasks self-audit failure.
- If `tasks` discovers missing upstream truth during remediation, route directly to `specify`, `plan`, or `deep-research`; run `analyze` again only when explicitly required by legacy or diagnostic state after upstream artifacts are repaired and tasks are regenerated.
- If the defect is execution-only with no upstream artifact drift, continue in `implement` or route into `debug`.
- If `analyze` is run after `implement` has already started or finished, treat the current implementation as provisional until the highest invalid stage has been repaired and downstream artifacts have been regenerated.

Boundary-sensitive implementation rule:

- If the feature touches an established boundary pattern in the target project, `plan` should write an `Implementation Constitution` section instead of leaving that rule buried in technical background.
- Use `Implementation Constitution` for architecture invariants, boundary ownership, forbidden implementation drift, required implementation references, and review focus.
- Typical triggers include existing framework-owned boundaries, native/plugin bridges, protocol seams, generated API surfaces, or any area where "generic implementation instinct" would likely drift from the repository's established pattern.
- A good heuristic is: if an implementer should be forced to inspect specific existing boundary files before coding safely, the feature likely needs `Implementation Constitution`.
- `tasks` should convert those rules into task-local guardrail refs in canonical `task-index.json` before setup or feature work begins.
- `implement` should treat those refs as binding execution constraints and resolve the touched boundary's owning framework, defining references, and forbidden drift before changing code.
- Delegated execution must not rely on raw task text when architecture or quality rules matter.
- `plan` should provide `Dispatch Compilation Hints`.
- `implement` should compile and validate a `WorkerTaskPacket` just in time only for delegated work; leader-direct tasks do not need packet boilerplate.
- Subagent packets should carry platform guardrails when a lane depends on supported-platform constraints, conditional compilation, or environment-sensitive runtime assumptions.

Current `sp-implement` runtime model in Spec Kit Plus:

- `sp-implement` uses `execution_model: adaptive`; the leader owns route selection, execution state, acceptance, and recovery
- one small or tightly coupled task may run `leader-direct`; one independent bounded task may use `one-subagent`; isolated ready lanes with an explicit join may use `parallel-subagents`
- delegated packets are compiled just in time from the current task, live code, and stable contract refs; a dispatch failure triggers route re-evaluation rather than an automatic local fallback
- durable teams/runtime execution is the `managed-team` surface (`sp-implement-teams` / `sp-teams`) for durable state or lifecycle needs, not an internal fallback hidden inside `sp-implement`
- subagents should execute from compiled `WorkerTaskPacket` contracts rather than rediscovering rules from background context
- native planning, task-generation, research, review, quick, debug, and PRD-scan lanes submit through their stage-owned `specify-runtime result submit --result-json '<inline-json>'` channel; native implementation workers return inline results for leader-owned `specify-runtime implement result-merge`, while only an explicitly selected durable Teams run uses its owning `submit-result` command
- `specify-runtime result path` emits JSON directly and does not accept `--format`; do not append `--format`
- a managed dispatch supplies its request id; an unmanaged implementation, quick, debug, planning, task-generation, or research lane supplies the owning workflow/workspace/session and lane identifiers accepted by `result submit`
- never compute, create, edit, rename, or delete a result path directly, and never ask a subagent to emit a result file; build the bounded envelope in memory and pass it inline
- `specify-runtime result path` is discovery-only compatibility output; `result submit` remains the mutation boundary even when no managed dispatch request exists
- when subagent language is normalized into canonical orchestration state, preserve the raw `reported_status`
- task decomposition should stay progressive: compile only the current executable window instead of pre-generating worker packets for later batches that still depend on upstream evidence
- parallel work is coordinated through explicit join points before dependent work continues
- native lifecycle discovery requires the integration's actual dispatch and join surfaces, not a guessed cleanup API; an accepted terminal result completes the lane, and interruption or cancellation is only for unfinished work that must stop
- every join point that gates downstream work should name a validation target, a validation command or check, and a pass condition
- grouped parallelism is the default when ready tasks have isolated write sets; use a pipeline shape only when outputs must flow stage-by-stage and keep explicit checkpoints between stages
- review is event-triggered by drift, parallel joins, write-scope violations, validation failures, worker concerns, obligation conflicts, real-entrypoint gaps, or a review-window threshold; it is not repeated mechanically for every task
- runtime surfaces can report retry-pending work and blockers instead of hiding those states in chat-only narration
- blocked subagent results should carry the blocker, the failed assumption, and the smallest safe recovery step so the leader can fail fast instead of guessing
- if a subagent lane reports `completed` or drifts into `idle` before the promised handoff arrives, treat it as a stale lane and recover explicitly instead of assuming success
- established boundary patterns should be preserved through `Implementation Constitution` and implementation guardrails, not rediscovered ad hoc during coding

Shared runtime-facing guidance across integrations:

- `sp-implement`, `sp-debug`, and `sp-quick` now all carry shared leader and result handoff expectations across Markdown, TOML, and skills-based integrations. The full `sp-quick` branch gates substantive execution on the one-time runtime Decision Checkpoint; the full `sp-debug` branch gates substantive investigation on the Debug Understanding Checkpoint and then uses complexity-based leader-inline, subagent-assisted, or blocked session state. Their explicit context-direct branches stay outside those durable workflow states.
- The shared contract is integration-neutral: leader role, join-point discipline, structured handoff expectations, and `reported_status` preservation are common across CLIs. Workflow-specific fallback semantics stay explicit in the command guidance.
- Only the concrete dispatch and join commands remain integration-specific. For example, Codex names `spawn_agent` and `wait_agent`; completed agents are already terminal, and `sp-teams` is used only when durable team state is explicitly needed.

For Codex and other skills-based integrations, the generated commands are installed in skills form. Codex now uses the dedicated `.codex/skills/` directory for generated skills.

Skills-based projects now install two layers into the same skills directory:

- explicit workflow skills: `sp-*`
- passive bundled skills: keep the directory names from `templates/passive-skills/` (for example `spec-kit-*`, `spec-kit-discussion-handoff-review`, `tdd-workflow`, `frontend-design`)

`sp-*` remains the primary user-facing workflow surface. Passive skills keep their template names and exist to improve automatic routing, guardrails, and bundled capabilities inside Spec Kit Plus repositories, not to replace the explicit workflow commands.

The advanced workflow profile installs the independent `spx-*` skills from
`templates/advanced-skills/` plus exactly the unchanged Classic map companions
`sp-map-scan`, `sp-map-build`, and `sp-map-update`. It does not install any
other Classic workflow skill or the Classic passive-skill layer during that
init run. Running init again with the classic profile adds those layers
alongside the SPX skills.

## Multi-CLI Orchestration

Current orchestration status in Spec Kit Plus:

- generic orchestration core exists under `src/specify_cli/orchestration/`
- `sp-plan` and `sp-tasks` are adaptive: `execution_model: adaptive`, `execution_mode: light | standard | heavy`, `dispatch_shape: leader-inline | one-subagent | parallel-subagents | subagent-blocked`.
- Adaptive `sp-plan`/`sp-tasks` use leader-inline for light work, native subagents for standard work when available, leader-inline degradation with `capability_degraded: true` only for standard native-unavailable work without high-risk triggers, and `subagent-blocked` for standard no-safe-lane or unpacketizable work plus heavy/safety-critical unavailable or unpacketizable work; managed-team fallback is not part of adaptive plan/tasks dispatch.
- `sp-implement` is adaptive and uses just-in-time packets only for delegated lanes. Workflows that remain mandatory-subagent, such as `sp-quick`, `sp-map-scan`, `sp-map-build`, `sp-prd-scan`, and `sp-prd-build`, still use `execution_model: subagent-mandatory`. `sp-debug` records its own session-level `execution_model: leader-inline | subagent-assisted | blocked`.
- in execution-oriented workflows, use subagent execution only when a validated `WorkerTaskPacket` or equivalent execution contract preserves quality
- `specify`, `plan`, `tasks`, and `explain` now document workflow-specific lanes and join points while keeping shared workflow templates integration-neutral
- `sp-teams` remains the Codex `managed-team` execution surface for durable team state, explicit join-point tracking, durable request results, or lifecycle control beyond one in-session subagent burst; ordinary native `sp-*` and `spx-*` lanes keep their stage-owned result channels
- Claude, Gemini, and Copilot ship initial adapter skeletons (alongside Codex) for native-first capability reporting
- durable runtime maturity for `implement` and `debug`, plus wider integration rollout, remain future work

This repository is no longer only a Milestone 1 slice, but the full execution/runtime maturity roadmap is still not complete.

## Codex Team Runtime

Spec Kit Plus exposes a Codex-only team/runtime surface. In a
terminal, enter through the `specify` CLI:

```bash
specify sp-teams --help
```

Inside Codex, the generated agent skill is invoked as `$sp-teams`.

### The `specify sp-teams` terminal surface

`specify sp-teams` is the official shell CLI surface for the runtime. Avoid
advertising a bare `sp-teams` executable because the package does not install
one.

- `specify sp-teams watch` opens a full-screen observer over members and flow, with lightweight terminal interaction for focus switching, detail expansion, and view cycling.
- `specify sp-teams status` dumps the latest JSON snapshot of the team phase, worker roster, task queue, and mailbox state.
- `specify sp-teams await` blocks until the runtime reaches a terminal phase so operators can wait for batch completion.
- `specify sp-teams resume` re-attaches to an existing runtime session by replaying the metadata in `.specify/teams/` and restarting the tmux backend.
- `specify sp-teams shutdown` requests a graceful stop, letting workers finish or fail their in-flight tasks before tearing down.
- `specify sp-teams cleanup` removes `.specify/teams/` state after shutdown succeeds; run it only once shutdown has settled to avoid corrupting the state folder.
- `specify sp-teams submit-result --request-id <id> --result-json '<inline-json>'` validates and records a structured subagent result for an existing dispatch. Use `specify sp-teams result-template --request-id <id>` only to inspect the canonical `pending` shape; do not submit that template unchanged or materialize it as a temporary result file.
- `specify sp-teams api <operation>` proxies structured JSON operations (task claims, worker heartbeats, events) into the runtime; use it when automation needs a predictable channel.

For agents and automation, prefer the optional MCP supplement instead of having the model compose CLI invocations directly:

- `specify-teams-mcp` exposes an agent-facing MCP facade for the structured control plane
- install the optional Spec Kit Plus facade with `uv tool install --force "specify-cli[mcp] @ git+https://github.com/chenziyang110/spec-kit-plus.git"`; Codex config can register it only when that extra is available
- if you install the MCP extra after project init, refresh the generated Codex config with `scripts/sync-ecc-to-codex.sh` or `scripts/powershell/sync-ecc-to-codex.ps1`
- the MCP layer is intended for agent/tool consumers
- `specify sp-teams` remains the human/operator CLI and parity fallback surface

This command suite powers both the `sp-teams` skill and the runtime APIs that downstream tooling relies on, which is why the command is restricted to Codex-initiated projects.

### Runtime state location and lifecycle

All runtime state lives under `.specify/teams/`:

- `runtime.json` contains the active session metadata and canonical root paths.
- `state/` holds per-object JSON files (`tasks/*.json`, `workers/*.json`, `mailboxes/*.json`, `dispatch/*.json`) along with `phase.json` and `events.log` for the lifecycle stream.
- Heartbeats, claims, approvals, and monitor snapshots append to the files under `state/`, helping the CLI restart from the latest saved facts.

Lifecycle notes:

- Tasks run through `pending -> in_progress -> completed|failed` and emit events that `specify sp-teams status` surfaces.
- Workers claim tasks with identity records, write heartbeats under `state/workers`, and consume mailbox messages from `state/mailboxes`.
- Structured subagent results live under `state/results/` and are submitted through `specify sp-teams submit-result` / `specify sp-teams api submit-result` before `complete-batch` should mark a structured-result batch done.
- `specify sp-teams shutdown` appends the terminal event through the Teams control plane, and `specify sp-teams cleanup` removes `.specify/teams/` only after the CLI has archived all JSON state.

Operators should treat this directory as the single source of truth for resumes, restarts, and audits, and not attempt to recreate state outside the official CLI surface.

### Operator guidance and backend requirements

- The runtime currently requires a tmux-capable backend (`tmux` on Unix/WSL or a Windows-compatible alternative) to host worker panes; the CLI validates the backend before bootstrapping a session.
- `specify sp-teams watch` is the operator-facing live board: use it when you need a continuous view of members and flow instead of one-shot diagnostics.
- Use `specify sp-teams resume` whenever a previously-running session still holds worker heartbeats or task claims to prevent duplicate boots.
- Issue `specify sp-teams shutdown` before terminating the tmux backend so the runtime can flush claims and notify join points, then run `specify sp-teams cleanup` once the CLI reports the phase is `shutdown`/`cleaned`.
- `specify sp-teams await` is useful for scripts that need to pause until the team exits the `dispatch` phase without polling `state/` files directly.

### Release isolation guidance

Current release scope:

- Codex-only in the current release scope
- requires a tmux-capable environment
- installs the Codex team skill as `sp-teams`
- keeps non-Codex integrations free of the team/runtime surface by default
- installs runtime helper assets only under `.specify/teams/` for Codex projects

Existing Codex projects may use an optional upgrade path, but that upgrade remains optional and non-blocking rather than a requirement for other integrations.

Release isolation guidance:

- `specify init --ai codex` may generate `sp-teams` and `.specify/teams/*`
- non-Codex init flows must not generate `sp-teams`, `.specify/teams/*`, or advertise `sp-teams`
- `omx` and `$team` are not the supported product surface for this repository

Maintainer note:

- keep Codex team assets and messaging behind Codex-only install and help paths unless the release boundary is intentionally widened

## Key Commands

- `specify init`
  - Command shape: `specify init <project> --ai <agent>`
- `specify check`
- `specify extension list`
- `specify preset list`

### UI Design Change Runtime Helpers

- The checked-in `templates/design-preview-template.html` is generated from the
  upstream-only Jinja source in `src/specify_cli/design_preview_source/`. Run
  `uv run python scripts/render-design-preview-template.py` after changing a
  focused partial, or add `--check` to verify synchronization. Generated
  projects receive only the self-contained compatibility HTML and compact
  editable manifest, not the Jinja source tree.
- `specify-runtime design change UD-0001 --title "..." --type overhaul
  --scope web:orders --profiles web` creates one bounded workspace and ensures
  `.specify/design/index.json` exists without creating a root `DESIGN.md`.
- `specify-runtime design iterate UD-0001 UD-0002 --title "..." --scope
  web:orders/detail` creates a successor pinned to the registered source's
  exact SHA-256 and lineage without mutating it. The requested scope must still
  be active on that source; an excluded subtree iterates from its active
  successor instead.
- `specify-runtime design resolve --scope web:orders/detail` discovers active
  candidates only. A composite result must be split into independently bound
  consumer units because the current binding artifacts are singular.
- `specify-runtime design diff UD-0001 UD-0002` compares lineage, scope,
  stable decisions, handoff contracts, and changed sections before adoption.
- `specify-runtime design impact feature:001-orders --change UD-0002 --scope
  web:orders/detail --mode formal --expected-change UD-0001` is a read-only,
  scope-bounded adoption preview. It CAS-checks the current receipt and returns
  impact classes, affected `DS-*`/`DH-*` IDs, `preserved_bindings`,
  `invalidated_bindings`, `reconcile_from`, reconciliation actions, and a
  canonical `impact_sha256`.
- `specify-runtime design preview-manifest --out
  .specify/design/changes/UD-0001/previews/round-NN.manifest.json --profiles web,mobile` writes
  the compact editable source for a review round from the canonical capability
  registry. `specify-runtime design profiles` lists the supported `web`,
  `mobile`, `desktop`, `cli`, `tui`, `content`, and `no-ui` routes. Visual
  profiles project surface-native capabilities, specimens, states, targets, and
  production units into every direction; `no-ui` instead requires current
  not-applicable evidence and creates no preview artifact.
- `specify-runtime design lint .specify/design/changes/UD-0001/DESIGN.md --level structural` checks schema and reference shape;
  `specify-runtime design lint .specify/design/changes/UD-0001/DESIGN.md --level ready` additionally requires an approved,
  project-specific direction whose image-primary or HTML-primary visual round,
  approval sidecar, immutable
  handoff, hashes, design decisions, handoff contracts, modes,
  responsive/content rules, and verification contract agree.
- `specify-runtime design preview --out .specify/design/changes/UD-0001/previews/round-NN.html`
  is the HTML-primary fallback and scaffolds one unfinished concept canvas; add
  `specify-runtime design preview --manifest .specify/design/changes/UD-0001/previews/round-NN.manifest.json` to
  deterministically render the structural draft, then replace its visible seed
  with professional project-specific HTML before ready lint;
  `specify-runtime design preview-lint PATH --level ready` validates a configured
  candidate. When live image generation is available, generate one
  `round-NN.png|jpg|jpeg|webp` concept plus `round-NN.prompt.md` beside the same
  manifest, then approve it with `--manifest`, `--prompt`,
  `--image-inspection`, and `--image-editing`. `specify-runtime design approve`
  freezes either selected medium and materializes both its byte-bound approval
  sidecar and immutable `.handoff.json` implementation contract, including the
  exact ordered capability profiles and `SP-*` specimen set needed to reproduce
  the approved direction without treating either review carrier as production
  implementation.
- `specify-runtime design export .specify/design/changes/UD-0001/DESIGN.md --format json` exports normalized design tokens and component token references after ready validation.
- `specify-runtime design export .specify/design/changes/UD-0001/DESIGN.md --format tailwind` exports supported token categories into Tailwind theme fields after ready validation.
- `specify-runtime design register .specify/design/changes/UD-0001/DESIGN.md` makes the ready, approved change consumable and pins its document digest in `.specify/design/index.json`; overlapping approved scope requires explicit `supersedes` metadata.
- Formal adoption uses `specify-runtime design adopt feature:<feature-id>
  --change UD-0002 --scope web:orders/detail --mode formal --binding-ref
  <feature-dir>/spec-contract.json --binding-sha256 <sha256>
  --expected-change UD-0001|none` after Specify writes the exact four fields.
  The receipt drives reconciliation from Specify, Plan, Review, or none; only
  listed downstream bindings and affected-scope Review evidence become pending,
  while completed implementation and unaffected evidence remain preserved.
- Post-Specify adoption keeps the planning-ready source spec byte-identical and
  uses `specify-runtime design adopt feature:<feature-id> --change UD-0002
  --scope web:orders/detail --mode formal-post-specify --binding-ref
  <feature-dir>/spec-contract.json --binding-sha256 <source-spec-sha256>
  --expected-change UD-0001|none`. Plan verifies it read-only with
  `specify-runtime design adoption feature:<feature-id> --scope
  web:orders/detail --binding-ref <feature-dir>/spec-contract.json
  --binding-sha256 <source-spec-sha256> --expected-change UD-0002`. The receipt
  is the late overlay; the source specification is never rewritten.
- Quick adoption uses `specify-runtime design adopt quick:<quick-id> --change
  UD-0002 --scope web:orders/detail --mode quick --binding-ref
  .planning/quick/<id>-<slug>/STATUS.md --binding-sha256 <sha256>
  --expected-change UD-0001|none`. First stage the exact scope and four
  registered fields as `decision.ui_confirmation.design_binding`, then confirm
  the checkpoint so sibling `confirmation.json` is `confirmed|inherited` and
  frontmatter says `understanding_confirmed: true`. Patch the independent
  top-level `## UI Design Binding` / `ui_design_binding` adoption copy only
  afterward; it must match the confirmation-protected decision copy. Hash those
  exact STATUS bytes before adoption. A replacement receipt retires unstarted
  affected packets, stops in-progress affected packets at a safe boundary,
  preserves completed work, creates a corrective work item for drift, and
  recaptures only affected Review evidence.
  Partial registration records parent `superseded_scopes` rather than retiring
  unaffected scope.
- Existing projects can use `--allow-unapproved` as a temporary structural-compatibility export while `sp-design`/`spx-design` records change-specific approval and provenance.
- `specify-runtime design import SOURCE_REFERENCE --out .specify/design/changes/UD-0001/references.md` records synthesis input for one design change; it does not overwrite either the change-local `DESIGN.md` or a legacy root file.
- `specify-runtime design ui-target --out FEATURE_DIR/ui-target.html` scaffolds a
  feature-level composition/state target, and `specify-runtime design ui-target-lint
  PATH --level ready` validates its manifest, review controls, approved design
  and handoff digests, decision and handoff contract IDs, responsive states, and
  self-contained runtime boundary.
- Substantive UI changes always materialize or preserve `ui-brief.md` through `specify-runtime design` or `specify-runtime artifact`; supplied
  screenshots, mockups, code references, design exports, URLs, existing pages,
  or "make it like this" language additionally route through Classic's CLI-owned
  `ui-reference-artifact` lane, which submits `ui-reference-notes.md` through
  `specify-runtime artifact` and creates optional `ui-target.html` only through
  `specify-runtime design ui-target`.
- Classic and Advanced use one current structured UI contract from spec through
  lifecycle evidence. Older UI version fields, duplicate fidelity payloads,
  untyped lifecycle evidence refs, and evidence-kind aliases are rejected;
  regenerate stale UI artifacts before continuing. A fidelity pass also
  registers `spec-kit-visual-comparison-v1` through `specify-runtime evidence`,
  binding the approved digests and design
  decision set to real-entrypoint captures, differences, tolerance, and
  pre-approved deviations.

Result helper command shapes:

- Native implementation result merge: `specify-runtime implement result-merge --feature-dir <feature-dir> --result-json '<inline-json>' --format json`
- Unmanaged non-Codex implementation path: `specify-runtime result path --command implement --feature-dir <feature-dir> --task-id <task-id>`
- Feature-stage native lane (Plan, Tasks, or Review): `specify-runtime result submit --command <feature-stage> --feature-dir <feature-dir> --lane-id <lane-id> --result-json '<inline-json>'`
- Deep Research worker result: `specify-runtime deep-research track-submit --feature-dir <feature-dir> --track-id <TRK-###> --attempt-id <ATTEMPT-###> --expected-revision <revision> --result-json '<inline-json>'`; the leader then uses `track-accept` or `track-reject`. Generic `result submit --command deep-research` is rejected.
- Command shape: `specify-runtime result path --command quick --workspace .planning/quick/<id>-<slug> --lane-id <lane-id>`
- Command shape: `specify-runtime result submit --command quick --workspace .planning/quick/<id>-<slug> --lane-id <lane-id> --result-json '<inline-json>'`
- Command shape: `specify-runtime result path --command debug --session-slug <session-slug> --lane-id <lane-id>`
- Command shape: `specify-runtime result submit --command debug --session-slug <session-slug> --lane-id <lane-id> --result-json '<inline-json>'`
- PRD-scan native lane: `specify-runtime result submit --command prd-scan --workspace <prd-scan-workspace> --lane-id <lane-id> --result-json '<inline-json>'`
- Durable Codex team path: `specify-runtime result path --command <workflow> --request-id <request-id>`
- Durable Codex team submission: `specify-runtime sp-teams submit-result --request-id <request-id> --result-json '<inline-json>'`

For the full CLI surface:

```bash
specify --help
specify init --help
```

## Supported Agents

Commonly used integrations in Spec Kit Plus include:

- `codex`
- `claude`
- `gemini`
- `copilot`
- `cursor-agent`
- `qwen`
- `opencode`
- `tabnine`
- `trae`
- `windsurf`
- `junie`
- `kilocode`
- `auggie`
- `roo`
- `codebuddy`
- `amp`
- `shai`
- `kiro-cli`
- `agy`
- `bob`
- `qodercli`
- `vibe`
- `zcode`
- `grok`
- `kimi`
- `mimo`
- `iflow`
- `pi`
- `forge`
- `generic`

The exact up-to-date list is available from the CLI:

```bash
specify init --help
```

## Repository Layout

Important directories:

- `src/specify_cli/` - CLI implementation and integrations
- `templates/` - built-in templates bundled into generated projects
- `scripts/` - shell and PowerShell support scripts
- `tests/` - regression and integration test suite
- `docs/` - installation, upgrade, and development notes

## Project Cognition Runtime

Navigation and technical truth are now cognition-first:

- Generated projects query `specify-runtime cognition status --format json` and use the task-local `specify-runtime cognition compass` packet as the advisory project cognition index. Status and database files are runtime implementation details; agents do not read or write them directly.
- Ordinary brownfield workflows should consume the status and compass CLI responses before broader repository analysis.
- `fresh` means the last handbook refresh completed against a known git baseline, and `specify-runtime cognition status --format json` exposes that git-baseline freshness truth.
- `support_drift` means support/tool-managed surfaces changed without proving runtime-truth staleness; resolve or ignore those support surfaces instead of treating them as a localized runtime refresh.
- `partial_refresh` means refresh data was recorded but the ready refresh check still failed; do not report refresh completion until readiness passes.
- `sp-map-scan` still performs diff-based scope selection when entered, but the refresh workbench remains internal to `map-scan` / `map-build`.
- Ordinary runtime consumption should prefer `debug-handbook.md` or `build-handbook.md` plus the workflow's fixed chapter set only as compatibility/export views.
- Generated workflows use `specify-runtime cognition compass --intent <intent> --query "$ARGUMENTS" --format json` as the default brownfield navigation intake and advisory navigation inputs. The packet returns readiness, `compass_state`, top-level `minimal_live_reads`, lane-level `first_pass_paths` with reasons, `coverage_diagnostics`, and `expansion_ref`.
- Agents read top-level `minimal_live_reads` first, then lane-level `first_pass_paths` reasons and compact `claim_refs`. A claim's `route_confidence` is valid only within `confidence_scope=route_candidate`; `state`, `freshness`, and `stale` describe graph lifecycle, not current truth. Advanced `specify-runtime cognition query` returns bounded top-level `claim_signals`, and `specify-runtime cognition expand --section claim_evidence` returns bounded evidence refs with `source_path` and `span`. All require live verification and cannot prove current repository truth or final edit scope.
- Compass claim-aware ranking is a bounded rerank after repository-backed matching: `match_score` establishes candidate eligibility, while `claim_ranking.adjustment` is capped at `+1` for fresh supported or graph-generation-verified claims, `-1` for stale, and `-2` for contradicted. Claims cannot create candidates and cannot replace live verification. Selected lanes with `stale_claim_signal` or `contradicted_claim_signal` remain `usable_with_review` and return `reconcile_claims_with_minimal_live_reads` plus a lane-specific live repository action.
- When the compass packet is draft-like, localized, missing coverage, or needs explicit concept decisions, the advanced path remains `specify-runtime cognition lexicon --mode catalog` -> agent-authored `semantic_intake` and `concept_decisions` -> `specify-runtime cognition query --query-plan`. In short: `lexicon -> semantic_intake -> query`. Facet coverage gates selection; top lexical or vector similarity alone is not route truth. Map points, code proves: navigation terms are route vocabulary, not evidence by themselves. CJK or mixed CJK/ASCII prompts still require agent-owned translation when using the advanced path. The advanced CLI tool's `agent_normalization` field remains agent semantic guidance, not a route decision. `templates/project-map/**` remains a historical compatibility/export surface for handbook generation, but new workflows should not read or require `.specify/project-map/**`.
- Precision `query` is exact-binding only: raw or rewritten natural-language text belongs to Compass/semantic intake. Agents page the catalog through `catalog_page.next_offset`, select current `concept_id` values or exact paths, carry the matching `lexicon_generation_id`, and consume a query only when `resolution_state=resolved_exact`; binding failures are explicit rather than null results.
- Releases publish prebuilt `specify-runtime` binaries for Windows, Linux, and macOS. Human `specify init`/upgrade resolves a trusted binary, stores it in a content-addressed user cache, and hardlinks or copies it to `.specify/bin/specify-runtime` (`.exe` on Windows). Project config persists only that relative entrypoint and its digest. `SPECIFY_RUNTIME_BIN` and PATH are bootstrap/repair seeds only; they are never rendered into agent commands.
- Empty projects initialized by `specify init` run `specify-runtime cognition init-empty` after pinning the binary. When there is no business code yet, this creates `.specify/project-cognition/status.json` and `.specify/project-cognition/project-cognition.db` with baseline kind `baseline_kind=greenfield_empty`; greenfield flows do not require map-scan -> map-build solely because the graph has no paths. Projects with existing code still use map-scan -> map-build when a full first brownfield cognition baseline is needed for a first/missing/unusable baseline, schema failure, an older schema or old broad-schema rebuild-required readiness, zero active-generation `path_index` rows, missing or invalid alias_index, `explicit_rebuild_requested`, or `baseline_identity_invalid`. Schema v5 is current-only: the runtime does not migrate schema v4 or older databases. Never move, remove, archive, or replace the store directly; run `specify-runtime cognition archive-incompatible-store --inspect --format json` and execute its hash-guarded `archive_argv` before the current `sp-map-scan -> sp-map-build` path.
- Workflow-owned mutation closeout is planner-first and explicit-scope: each source-changing `sp-*` workflow calls `specify-runtime cognition closeout-plan` with its registry-owned literal canonical id, `--scope-dir`, `--scope-mode explicit`, and one `--changed-path` per workflow-owned path; a rename owns both its old and new endpoint, and both must remain in `boundary.workflow_owned_paths`. It never derives the ID or edit boundary from environment variables, chat state, or a repository-wide rescan. The planner returns `update_mode`, agent-owned evidence fields, `unknown_path_dispositions`, and a structured `apply_argv`. Agents fill `payload_draft` in memory or the delta append draft, then execute `apply_argv`; `update_argv` remains low-level compatibility/debug only. Inline payloads accept `verification` plus `verification_evidence`, and `generated_surfaces` plus `generated_surface_notes`. Shared `specify-runtime cognition closeout apply` rejects absent or failed passing evidence before mutation, performs update and build validation, completes refresh only when globally eligible, and writes a receipt bound to the current update/status. It reports `scope_result_state`/`scope_partial_reasons` separately from project-wide `result_state`/`global_freshness`/`global_debt_reasons`, so `scope_ready` can close the current workflow while unrelated historical debt stays visible. `sp-map-update` remains the external/manual maintenance workflow for user edits, interrupted workflow repair, explicit map maintenance, and follow-up repair.
- Closeout agents should use `known_unknowns` only for blockers that make the cognition update unsafe to trust. If unrelated dirty or untracked working-tree paths were excluded by explicit workflow-owned paths, record that as `confidence_notes` or `boundary.initial_dirty_paths`, not as blocking `known_unknowns`.
- Use `map-update` for localized stale cognition refresh recommendations, external/manual changed-path map maintenance, and ordinary existing-baseline gaps; use `map-scan` followed by `map-build` only for first/missing/unusable baseline, schema failure, schema v1 or old broad-schema rebuild-required readiness, zero active-generation `path_index` rows, missing or invalid `alias_index`, `explicit_rebuild_requested`, or `baseline_identity_invalid`.
- For the first brownfield cognition baseline, run `sp-map-scan` followed by `sp-map-build` when you want a map baseline. That pair is map-maintenance complete only when scan acceptance and build acceptance pass: `specify-runtime cognition validate-scan --format json` and `specify-runtime cognition validate-build --format json`. Ordinary workflows may continue from live repository evidence when the map is missing, stale, or blocked.
- `sp-map-scan` scan artifacts should emit canonical fields (`id`, `type`, `title`, `paths`, `source_id`, `target_id`, `attrs`, and coverage `rows`). The runtime accepts compatibility aliases such as `node_id`, `kind`, `label`, `source_node_id`, `target_node_id`, `attrs_json`, and coverage `coverage`, but `sp-map-build` creates `path_index` rows from `nodes[].paths`; `coverage.json` is coverage accounting, not a path-index source. Coverage or coverage-ledger rows do not prove a path was scanned unless a concrete scan packet assigned the path and that packet's worker result reported packet-local coverage.
- After a successful `sp-map-update`, committing the refreshed source changes does not require a full rebuild by itself. A `ready` or `no_op` update must pass `specify-runtime cognition validate-build` with `status=ok` and `readiness=query_ready`, creating a receipt bound to the latest update ID, outcome, and active generation, before `specify-runtime cognition complete-refresh` may finalize freshness. Until then, the runtime gate withholds Compass/query as `update_finalization_pending`. `specify-runtime cognition record-refresh` is compatibility-only when that matching receipt already exists; it cannot bypass validation. Preserve `partial_refresh`, `needs_rebuild`, `blocked`, and `recorded` without finalization.
- Project cognition ignore rules live in root `.cognitionignore` or `.specify/project-cognition/.cognitionignore`. They use gitignore-compatible patterns and are honored by `map-scan`, `map-build`, and `map-update`; excluded paths must not enter project cognition graph evidence, runtime route indexes, or `minimal_live_reads`. `specify-runtime cognition generate-ignore --format json` writes a starter `.specify/project-cognition/.cognitionignore`, returns `review_required=true` plus decision-bearing `suggested_patterns` when review is needed, and never overwrites an existing ignore file. A created starter with no suggestions returns `review_required=false`.
- `specify-runtime cognition confirm-ignore --all-suggested --format json` (or repeated exact `--pattern` values for an approved subset) is the runtime-owned transition from reviewed starter suggestions to active rules. Chat confirmation alone does not alter the scan boundary, and agents do not edit the runtime-owned ignore file.
- `specify-runtime cognition scan-set --out .specify/project-cognition/tmp/scan-files.json --format json` is the runtime scan-set resolution contract for agent-facing scan handoffs. It produces compact stdout with only the temporary file-list path and count; the file list itself contains only `files`.
- Project cognition is code-serving evidence, not an equal-depth archive. After `scan-set`, `scan-formats` inventories every repository-specific format cohort using detected format/family, path kind, top-level directory, and Git state, exposing only aggregate counts and at most three representatives. The Agent proposes one complete cohort-level policy (`semantic_scan`, `sample`, `inventory_only`, `exclude`, or `split_required`), `scan-policy-stage` validates exact coverage, and the user confirms the exact proposal digest before `scan-policy-confirm` activates it. Known cohorts reuse their confirmed decision across ordinary content/membership drift; newly observed cohorts require another exact proposal and confirmation. `scan-prepare` rejects missing, tampered, incomplete, unresolved, or newly uncovered policy state and freezes the current inventory plus confirmed policy into the workbench. This lets custom code formats be selected deliberately without turning Agent judgment into unconfirmed path-level filtering. Ordinary untracked source stays eligible, but untracked `.gitignore` matches, local runtime vendor/data/log payloads, and generated agent/workflow state default to inventory-only `P3`. `--include-gitignored` remains an explicit reviewed pre-policy input; it does not bypass the confirmed cohort decision. `scan-status.recommended_parallel_workers` is capped at four and may be reduced further by available agent slots.
- Advanced rebuilds run `specify-runtime cognition scan-prepare --scan-set .specify/project-cognition/tmp/scan-files.json --format json` to create or resume the deterministic, context-budgeted workbench and disjoint packet queue. Pass the model context window plus real instruction/inherited/reasoning/tool/result reserves, or an already-computed `--worker-budget-tokens`; packet estimates must fit the selected worker. Existing incompatible/in-progress workbenches are protected by default; `--force` explicitly discards current accepted and pending work but may replay validated cache, while `--full-rebuild` bypasses cache. The leader drives only `pending_path_count` through `scan-status` and `scan-lease`; an oversized packet remains undispatched until a worker with sufficient effective capacity is selected through `--worker-capacity-tokens`. Each low-cost worker receives a CLI-generated task brief, fills the supplied result shape in memory, and submits bounded progress through the brief's `scan-checkpoint --result-json '<inline-json>'` command; only the runtime materializes pending-result and checkpoint artifacts. If capacity is running out, `scan-yield` preserves the validated subset and requeues exactly the remaining paths for a new attempt; if a worker stops first, the leader uses the active lease from `scan-status` with `scan-requeue`. A fully checkpointed attempt is finalized with `scan-accept --packet-id <packet-id> --attempt-id <attempt-id> --format json`. The runtime—not a natural-language completion claim—validates path accounting, evidence, concrete `nodes[].paths`, generation-scoped attempt identity, and cumulative sequence before merging. Only after every packet is accepted may `validate-scan` issue the generation-, source-, and artifact-bound `scan-receipt.json`; `build-from-scan` rejects a missing or stale v2 receipt before graph-store mutation. Repeating build for the same receipt/compiler/schema fingerprint returns `reused=true` with the same ready generation and still runs `validate-build`.
- For cross-project references, run `specify-runtime cognition discover --root <path> --format json`
  before broad inspection. Use another project's cognition only when the CLI
  response reports `reference_readiness=ready`, `freshness=fresh`, and
  `graph_ready=true`. Do not probe its status/database files; do not treat legacy
  `.specify/project-map/**` outputs as current truth
  when the reference is stale, blocked, or incomplete.
- Generated projects run every agent-facing helper through the relative project
  `runtime_launcher` at `.specify/bin/specify-runtime` (`.exe` on Windows).
  `SPECIFY_RUNTIME_BIN` and PATH are considered only while a human bootstrap or
  upgrade provisions/repairs that project entrypoint.
- If a first baseline or structural rebuild can be completed now, run `sp-map-scan` followed by `sp-map-build`; `sp-map-build` owns `specify-runtime cognition build-from-scan --format json`, then `specify-runtime cognition validate-build --format json`, and publishes the query-ready baseline. Use `specify-runtime cognition complete-refresh --format json` only for non-build maintenance or incremental freshness flows such as successful `sp-map-update`; otherwise run `specify-runtime cognition mark-dirty --reason "<reason>" --format json` as the manual override/fallback.
- Map points, code proves: technical claims must be backed by live code, tests, scripts, configuration, or authoritative docs.
- This repository does not treat its own root `.specify/` directory as committed source-of-truth content; repo-local `.specify/` state is disposable and may be regenerated.
- After a successful refresh, record the new fresh cognition baseline. Use dirty fallback metadata only when the required refresh cannot be completed now, so same-feature resume can warn instead of self-blocking while upstream brownfield entrypoints and other features still require refresh.
- Any code change that alters project cognition meaning must update the cognition runtime. Workflow-owned mutation closeout is planner-first for normal `sp-*` work; use `sp-map-update` for external/manual map maintenance and follow-up repair.

## Reference documentation links

- [Installation Guide](docs/installation.md)
- [Upgrade Guide](docs/upgrade.md)
- [Local Development](docs/local-development.md)
- [GitHub Spec Kit methodology reference](https://github.com/github/spec-kit/blob/main/spec-driven.md)

## Spec Kit Plus Notes

- install from `chenziyang110/spec-kit-plus` when you want the capabilities documented here
- the Codex integration defaults to skills-mode behavior; `--ai-skills` is usually unnecessary
- templates, runtimes, and workflow behavior evolve independently from GitHub Spec Kit

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).

</details>
