---
description: "Force cleanup of dangling tmux panes and temporary worktrees created by AgentTeams"
---

# AgentTeams Cleanup

Forceful cleanup of state and sandboxes left behind by interrupted runs.

## Steps

1. Find all tmux sessions matching prefix from config.
2. Force kill panes and sessions.
3. Git prune and remove temporary worktrees.

```bash
node .specify/extensions/agent-teams/engine/src/cli/cleanup.js
```
