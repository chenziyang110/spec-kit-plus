// cleanup.js
// Script to forcefully tear down tmux sessions and worktrees created by the engine

const { spawnSync } = require('child_process');

console.log("Cleaning up AgentTeams sandboxes...");

// 1. Clean up tmux sessions
const TMUX_PREFIX = 'sp-team-'; // Loaded from config in a real implementation
console.log(`-> Searching for tmux sessions with prefix '${TMUX_PREFIX}'`);

try {
    const lsResult = spawnSync('tmux', ['ls', '-F', '#{session_name}'], { encoding: 'utf-8' });
    if (lsResult.status === 0) {
        const sessions = lsResult.stdout.split('\n').filter(s => s.startsWith(TMUX_PREFIX));
        for (const session of sessions) {
            console.log(`Killing tmux session: ${session}`);
            spawnSync('tmux', ['kill-session', '-t', session]);
        }
    }
} catch (e) {
    console.log("No tmux sessions found or tmux is not running.");
}

// 2. Clean up git worktrees
console.log("-> Searching for temporary git worktrees...");
try {
    const listResult = spawnSync('git', ['worktree', 'list'], { encoding: 'utf-8' });
    if (listResult.status === 0) {
        const lines = listResult.stdout.split('\n');
        for (const line of lines) {
            // Target worktrees stored in the .specify/agent-teams directory
            if (line.includes('.specify/agent-teams/worktrees/worker-')) {
                const pathMatch = line.match(/^([^\s]+)/);
                if (pathMatch) {
                    const wtPath = pathMatch[1];
                    console.log(`Removing worktree: ${wtPath}`);
                    spawnSync('git', ['worktree', 'remove', '-f', wtPath]);
                }
            }
        }
    }
    
    // Prune just to be safe
    spawnSync('git', ['worktree', 'prune']);
} catch (e) {
    console.log("Failed to clean git worktrees (maybe not in a git repo).");
}

console.log("\nCleanup complete.");
