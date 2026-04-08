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
2. `specify` to write the feature spec
3. `plan` to define implementation design
4. `tasks` to break work into executable tasks
5. `implement` to execute the task plan

For Codex and other skills-based integrations, the generated commands are installed in skills form.

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
