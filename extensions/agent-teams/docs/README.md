# Agent Teams Extension

A bundled multi-agent execution extension for `spec-kit-plus`. It reads the active feature's `tasks.md`, writes an AgentTeams ledger under `.specify/agent-teams/state`, seeds required worker assets into project-local `.codex/`, and launches the upstream oh-my-codex runtime locally.

## Installation

You can install this extension directly via the spec-kit CLI:

```bash
specify extension add agent-teams
```

## Usage

This extension provides two main commands:

### 1. Run Team Execution
```bash
/sp.agent-teams.run
```
Parses the active feature's `spec.md` and `tasks.md`, provisions isolated Git worktrees, and launches tmux-backed workers to execute the task graph concurrently.

### 2. Cleanup
```bash
/sp.agent-teams.cleanup
```
Forcefully kills any dangling Tmux panes and removes temporary Git worktrees created by the engine.

## Configuration

You can customize the engine's behavior by editing the generated `.specify/extensions/agent-teams/agent-teams-config.yml` file.

```yaml
# How many workers to run in parallel
concurrency: 3

# Maximum number of times the verification loop can fail before aborting a task
max_fix_attempts: 3
```

## Architecture

This extension vendors the runtime sources it needs directly inside `extensions/agent-teams/engine/`:

- Rust workspace crates for `omx-runtime`, `omx-mux`, and `omx-runtime-core`
- TypeScript runtime/orchestrator sources from `oh-my-codex`
- bundled role prompts and the `worker` skill used by spawned panes

On first run it will:

1. install the engine's local Node.js dependencies,
2. compile the bundled TypeScript runtime,
3. compile the local Rust `omx-runtime` binary,
4. sync missing `worker` skill and prompts into project-local `.codex/`,
5. translate the feature task graph into AgentTeams ledger files, and
6. start the local runtime against `.specify/agent-teams/state`.
