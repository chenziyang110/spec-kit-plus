import { existsSync, readdirSync, readFileSync, rmSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import yaml from 'js-yaml';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const DEFAULT_CONFIG = {
  sandbox: {
    worktree_dir: '.specify/agent-teams/worktrees',
    state_dir: '.specify/agent-teams/state',
    tmux_prefix: 'sp-team-',
  },
};

function loadConfig(projectRoot) {
  const configPath = resolve(projectRoot, '.specify', 'extensions', 'agent-teams', 'agent-teams-config.yml');
  if (!existsSync(configPath)) return DEFAULT_CONFIG;

  const raw = yaml.load(readFileSync(configPath, 'utf8'));
  return {
    ...DEFAULT_CONFIG,
    ...(raw && typeof raw === 'object' ? raw : {}),
    sandbox: {
      ...DEFAULT_CONFIG.sandbox,
      ...((raw && typeof raw === 'object' && raw.sandbox) || {}),
    },
  };
}

function discoverRuntimeSessions(stateRoot) {
  const teamRoot = join(stateRoot, 'team');
  if (!existsSync(teamRoot)) return [];

  const sessions = new Set();
  for (const teamName of readdirSync(teamRoot)) {
    const configPath = join(teamRoot, teamName, 'config.json');
    if (!existsSync(configPath)) continue;
    try {
      const config = JSON.parse(readFileSync(configPath, 'utf8'));
      if (typeof config.tmux_session === 'string' && config.tmux_session.trim()) {
        sessions.add(config.tmux_session.trim());
      }
    } catch {
      // ignore malformed config payloads during best-effort cleanup
    }
  }
  return [...sessions];
}

function killTmuxSessions(sessionNames, tmuxPrefix) {
  const names = new Set(sessionNames);
  const lsResult = spawnSync('tmux', ['ls', '-F', '#{session_name}'], { encoding: 'utf8' });
  if (lsResult.status !== 0) return;

  for (const session of lsResult.stdout.split(/\r?\n/).filter(Boolean)) {
    if (session.startsWith('omx-team-') || session.includes(tmuxPrefix) || names.has(session)) {
      spawnSync('tmux', ['kill-session', '-t', session], { encoding: 'utf8' });
    }
  }
}

function removeManagedWorktrees(worktreeRoot) {
  const resolvedWorktreeRoot = resolve(worktreeRoot);
  const listResult = spawnSync('git', ['worktree', 'list', '--porcelain'], { encoding: 'utf8' });
  if (listResult.status !== 0) return;

  const worktreePaths = listResult.stdout
    .split(/\r?\n/)
    .filter((line) => line.startsWith('worktree '))
    .map((line) => line.slice('worktree '.length).trim());

  for (const worktreePath of worktreePaths) {
    const resolvedPath = resolve(worktreePath);
    if (resolvedPath.startsWith(resolvedWorktreeRoot)) {
      spawnSync('git', ['worktree', 'remove', '-f', resolvedPath], { encoding: 'utf8' });
    }
  }

  spawnSync('git', ['worktree', 'prune'], { encoding: 'utf8' });
  rmSync(resolvedWorktreeRoot, { recursive: true, force: true });
}

function main() {
  try {
    const projectRoot = process.cwd();
    const config = loadConfig(projectRoot);
    const stateRoot = resolve(projectRoot, config.sandbox.state_dir);
    const worktreeRoot = resolve(projectRoot, config.sandbox.worktree_dir);
    const runtimeSessions = discoverRuntimeSessions(stateRoot);

    console.log('Cleaning up AgentTeams sandboxes...');
    killTmuxSessions(runtimeSessions, config.sandbox.tmux_prefix);
    removeManagedWorktrees(worktreeRoot);
    console.log('Cleanup complete.');
  } catch (error) {
    console.error(`agent-teams cleanup: ${error instanceof Error ? error.message : String(error)}`);
    process.exit(1);
  }
}

if (process.argv[1] === __filename) {
  main();
}
