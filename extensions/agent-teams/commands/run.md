---
description: "Parse tasks.md and execute them using an isolated multi-agent team"
scripts:
  sh: ../../scripts/bash/check-prerequisites.sh --json
---

# AgentTeams Executor

This command bridges the active feature's `tasks.md` with the bundled AgentTeams execution engine.

## Context

$ARGUMENTS

## Steps

1. Resolve the current feature directory and use that feature's `spec.md` and `tasks.md`.
2. Check if the internal AgentTeams engine is compiled (Rust/TS dependencies).
3. If missing, automatically run the build script `scripts/build-engine.sh`.
4. Translate feature tasks into AgentTeams JSON ledger records in `.specify/agent-teams/state`.
5. Sync bundled worker prompts/skills into the project-local `.codex/` tree when missing.
6. Provision isolated Git worktrees and tmux-backed workers through the bundled runtime.
7. Hand over execution to the local orchestrator and stream progress.

```bash
# 1. Execute engine build/check
bash .specify/extensions/agent-teams/scripts/build-engine.sh

# 2. Invoke the bridge entrypoint with the active feature artifacts
node .specify/extensions/agent-teams/engine/src/cli/bridge.js --spec <FEATURE_DIR>/spec.md --tasks <FEATURE_DIR>/tasks.md
```
