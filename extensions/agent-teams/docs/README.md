# Agent Teams Extension

A powerful extension for `spec-kit-plus` that provides a physically isolated, multi-agent execution engine. It parses your planned tasks and assigns them to autonomous agents running in isolated Tmux sandboxes.

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
Parses your `.specify/project-map/tasks.md`, provisions isolated Git worktrees, and launches Tmux panes for the agents to execute the tasks concurrently.

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

This extension packages a lightweight version of the `oh-my-codex` agent runtime.
When you run the command for the first time, it will automatically compile the Rust-based isolation engine and install the necessary Node.js orchestrator dependencies locally within the extension's folder. 
This ensures your global environment remains clean.
