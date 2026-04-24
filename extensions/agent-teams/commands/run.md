---
description: "Parse tasks.md and execute them using an isolated multi-agent team"
scripts:
  sh: ../../scripts/bash/check-prerequisites.sh --json
---

# AgentTeams Executor

This command bridges spec-kit tasks with the underlying oh-my-codex multi-agent execution engine.

## Context

$ARGUMENTS

## Steps

1. Check if the internal AgentTeams engine is compiled (Rust/TS dependencies).
2. If missing, automatically run the build script `scripts/build-engine.sh`.
3. Parse `.specify/project-map/tasks.md` and `.specify/project-map/spec.md`.
4. Translate spec-kit tasks into AgentTeams JSON Ledger format in `.specify/agent-teams/state`.
5. Provision isolated Git Worktrees and Tmux Panes for workers.
6. Hand over execution to the local orchestrator and stream progress.

```bash
# 1. Execute engine build/check
bash .specify/extensions/agent-teams/scripts/build-engine.sh

# 2. Invoke the bridge entrypoint to parse tasks and start the orchestrator
node .specify/extensions/agent-teams/engine/src/cli/bridge.js --spec .specify/project-map/spec.md --tasks .specify/project-map/tasks.md
```
