# Spec Kit Plus

`spec-kit-plus` is a maintained fork of Spec Kit focused on practical Spec-Driven Development workflow support for local AI coding agents.

This repository contains:

- the `specify` CLI
- built-in spec, plan, tasks, and implement templates
- agent integrations for tools such as Codex, Claude, Gemini, Copilot, Cursor, Windsurf, Kimi, Forge, and others
- the bundled scripts and assets used by `specify init`

## Install

### Persistent install from this fork

Install the CLI from this repository:

```bash
uv tool install specify-cli --from git+https://github.com/chenziyang110/spec-kit-plus.git
```

Upgrade to the latest version from this fork:

```bash
uv tool install specify-cli --force --from git+https://github.com/chenziyang110/spec-kit-plus.git
```

### One-time use without installing

```bash
uvx --from git+https://github.com/chenziyang110/spec-kit-plus.git specify init my-project --ai codex
```

Initialize the current directory with the latest fork version, without relying on whatever `specify` is currently on your `PATH`:

```bash
uvx --from git+https://github.com/chenziyang110/spec-kit-plus.git specify init . --ai codex
```

### Local editable install for development

```bash
git clone https://github.com/chenziyang110/spec-kit-plus.git
cd spec-kit-plus
uv pip install -e .
```

## Prerequisites

- Python 3.11+
- `uv`
- `git`
- your target AI agent CLI or IDE integration

## Quick Start

Create a new project:

```bash
specify init my-project --ai codex
```

Initialize the current directory:

```bash
specify init --here --ai codex
```

If the current directory is not empty:

```bash
specify init --here --force --ai codex
```

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

If you want templates without checking whether the agent tool is installed:

```bash
specify init my-project --ai codex --ignore-agent-tools
```

## Workflow

After `specify init`, use the generated workflow commands in your agent:

1. `constitution` to define project principles
2. `specify` to produce a planning-ready, analysis-first feature spec
3. `plan` to define implementation design
4. `tasks` to break work into executable tasks
5. `implement` to execute the task plan (supports autonomous loop via `/sp-autonomous`)

Mainline pre-planning flow:

```text
specify -> plan
```

Skill map after `specify init`:

- Core workflow skills: `constitution`, `specify`, `plan`, `tasks`, `implement`
- Support skills: `spec-extend`, `checklist`, `analyze`, `explain`
- Codex-only runtime: `specify team` and `sp-team`

Optional follow-up commands:

- `spec-extend` to deepen an existing spec before planning when analysis, references, or gaps need more work
- `checklist` to generate requirement-quality checklists after planning so the written requirements can be audited before implementation
- `analyze` to perform a cross-artifact consistency pass across `spec.md`, `context.md`, `plan.md`, and `tasks.md`
- `explain` to describe the current spec, plan, task, or implement artifact in plain language

Routing guide for lightweight work:

- `sp-fast` is only for trivial local fixes. Stay on that path only when the change is obvious, touches at most 3 files, and does not touch a shared surface.
- Move from `sp-fast` to `sp-quick` as soon as the work expands to more than 3 files, touches a shared surface, or needs research or clarification.
- `sp-quick` is for small but non-trivial work that still fits one bounded quick-task workspace.
- Move from `sp-quick` to `sp-specify` when the request spans multiple independent capabilities, carries compatibility or rollout risk, or needs explicit acceptance criteria before implementation.

After planning, continue with:

```text
tasks -> implement
```

Current `sp-implement` runtime model in this fork:

- `sp-implement` acts as a milestone-level orchestration leader rather than the direct executor
- concrete implementation runs through delegated execution paths (`single-agent`, `native-multi-agent`, or `sidecar-runtime`)
- parallel work is coordinated through explicit join points before dependent work continues
- runtime surfaces can report retry-pending work and blockers instead of hiding those states in chat-only narration

For Codex and other skills-based integrations, the generated commands are installed in skills form.

## Multi-CLI Orchestration (Milestones 1-2)

Current orchestration status in this fork:

- generic orchestration core exists under `src/specify_cli/orchestration/`
- `implement`, `specify`, `plan`, `tasks`, and `explain` now share the canonical strategy vocabulary: `single-agent`, `native-multi-agent`, and `sidecar-runtime`
- `specify`, `plan`, `tasks`, and `explain` now document workflow-specific lanes and join points while keeping shared workflow templates integration-neutral
- `specify team` remains the Codex compatibility surface for runtime-heavy execution
- Claude, Gemini, and Copilot ship first-release adapter skeletons (alongside Codex) for native-first capability reporting
- durable runtime maturity for `implement` and `debug`, plus wider integration rollout, remain future work

This repository is no longer only a Milestone 1 slice, but the full execution/runtime maturity roadmap is still not complete.

## Codex Team Runtime

This fork now exposes a Codex-only first-release team/runtime surface through:

```bash
specify team
```

### The `specify team` surface

`specify team` is the official CLI surface for the runtime. All operations start from this command, so avoid advertising other entry points such as `omx` or `$team`.

- `specify team status` dumps the latest JSON snapshot of the team phase, worker roster, task queue, and mailbox state.
- `specify team await` blocks until the runtime reaches a terminal phase so operators can wait for batch completion.
- `specify team resume` re-attaches to an existing runtime session by replaying the metadata in `.specify/codex-team/` and restarting the tmux backend.
- `specify team shutdown` requests a graceful stop, letting workers finish or fail their in-flight tasks before tearing down.
- `specify team cleanup` removes `.specify/codex-team/` state after shutdown succeeds; run it only once shutdown has settled to avoid corrupting the state folder.
- `specify team api <operation>` proxies structured JSON operations (task claims, worker heartbeats, events) into the runtime; use it when automation needs a predictable channel.

This command suite powers both the `sp-team` skill and the runtime APIs that downstream tooling relies on, which is why the command is restricted to Codex-initiated projects.

### Runtime state location and lifecycle

All runtime state lives under `.specify/codex-team/`:

- `runtime.json` contains the active session metadata and canonical root paths.
- `state/` holds per-object JSON files (`tasks/*.json`, `workers/*.json`, `mailboxes/*.json`, `dispatch/*.json`) along with `phase.json` and `events.log` for the lifecycle stream.
- Heartbeats, claims, approvals, and monitor snapshots append to the files under `state/`, helping the CLI restart from the latest saved facts.

Lifecycle notes:

- Tasks run through `pending -> in_progress -> completed|failed` and emit events that `specify team status` surfaces.
- Workers claim tasks with identity records, write heartbeats under `state/workers`, and consume mailbox messages from `state/mailboxes`.
- Shutdown requests append a terminal event, and cleanup removes the `.specify/codex-team/` directory once all JSON files have been archived.

Operators should treat this directory as the single source of truth for resumes, restarts, and audits, and not attempt to recreate state outside the official CLI surface.

### Operator guidance and backend requirements

- The runtime currently requires a tmux-capable backend (`tmux` on Unix/WSL or a Windows-compatible alternative) to host worker panes; the CLI validates the backend before bootstrapping a session.
- Use `specify team resume` whenever a previously-running session still holds worker heartbeats or task claims to prevent duplicate boots.
- Issue `specify team shutdown` before terminating the tmux backend so the runtime can flush claims and notify join points, then run `specify team cleanup` once the CLI reports the phase is `shutdown`/`cleaned`.
- `specify team await` is useful for scripts that need to pause until the team exits the `dispatch` phase without polling `state/` files directly.

### Release isolation guidance

Current release scope:

- Codex-only for first release
- requires a tmux-capable environment
- installs the Codex team skill as `sp-team`
- keeps non-Codex integrations free of the team/runtime surface by default
- installs runtime helper assets only under `.specify/codex-team/` for Codex projects

Existing Codex projects may use an optional upgrade path, but that upgrade remains optional, non-blocking release support rather than a first-release requirement.

Release isolation guidance:

- `specify init --ai codex` may generate `sp-team` and `.specify/codex-team/*`
- non-Codex init flows must not generate `sp-team`, `.specify/codex-team/*`, or advertise `specify team`
- `omx` and `$team` are not the supported product surface for this repository

Maintainer note:

- keep Codex team assets and messaging behind Codex-only install and help paths unless the release boundary is intentionally widened

## Key Commands

```bash
specify init <project> --ai <agent>
specify check
specify extension list
specify preset list
```

For the full CLI surface:

```bash
specify --help
specify init --help
```

## Supported Agents

Commonly used integrations in this fork include:

- `codex`
- `claude`
- `gemini`
- `copilot`
- `cursor-agent`
- `qwen`
- `opencode`
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
- `kimi`
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

## Documentation

- [Installation Guide](docs/installation.md)
- [Upgrade Guide](docs/upgrade.md)
- [Local Development](docs/local-development.md)
- [Spec-Driven Walkthrough](spec-driven.md)

## Notes For This Fork

- install from `chenziyang110/spec-kit-plus`, not the upstream `github/spec-kit`, if you want this fork's behavior
- Codex integration in this fork defaults to skills-mode behavior; `--ai-skills` is usually unnecessary
- template and workflow behavior may differ from upstream Spec Kit

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
