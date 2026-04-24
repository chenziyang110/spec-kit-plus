import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, rm, writeFile } from 'fs/promises';
import { join } from 'path';
import { tmpdir } from 'os';
import { execFileSync } from 'child_process';
import { monitorTeam } from '../runtime.js';
import {
  teamInit as initTeamState,
  teamReadConfig as readTeamConfig,
  teamSaveConfig as saveTeamConfig,
  teamListMailbox as listMailboxMessages,
  teamReadMonitorSnapshot as readMonitorSnapshot,
} from '../team-ops.js';
import { readTeamEvents } from '../state/events.js';

async function initRepo(): Promise<string> {
  const repo = await mkdtemp(join(tmpdir(), 'omx-empty-pick-repo-'));
  execFileSync('git', ['init', '-b', 'master'], { cwd: repo, stdio: 'ignore' });
  execFileSync('git', ['config', 'user.email', 'agent@example.com'], { cwd: repo, stdio: 'ignore' });
  execFileSync('git', ['config', 'user.name', 'Agent Teams Smoke'], { cwd: repo, stdio: 'ignore' });
  await writeFile(join(repo, 'README.md'), 'seed\n', 'utf-8');
  execFileSync('git', ['add', 'README.md'], { cwd: repo, stdio: 'ignore' });
  execFileSync('git', ['commit', '-m', 'seed'], { cwd: repo, stdio: 'ignore' });
  return repo;
}

async function addWorktree(repo: string, branch: string, prefix: string): Promise<string> {
  const worktree = await mkdtemp(join(tmpdir(), prefix));
  execFileSync('git', ['worktree', 'add', '-b', branch, worktree, 'HEAD'], { cwd: repo, stdio: 'ignore' });
  execFileSync('git', ['config', 'user.email', 'agent@example.com'], { cwd: worktree, stdio: 'ignore' });
  execFileSync('git', ['config', 'user.name', 'Agent Teams Smoke'], { cwd: worktree, stdio: 'ignore' });
  return worktree;
}

describe('monitorTeam empty cherry-pick handling', () => {
  it('treats an empty cherry-pick as already integrated instead of conflict noise', async () => {
    const repo = await initRepo();
    let workerPath = '';
    try {
      workerPath = await addWorktree(repo, 'wk1-empty-pick-branch', 'omx-empty-pick-wt-');

      await writeFile(join(workerPath, 'shared.txt'), 'same content\n', 'utf-8');
      execFileSync('git', ['add', 'shared.txt'], { cwd: workerPath, stdio: 'ignore' });
      execFileSync('git', ['commit', '-m', 'worker adds shared file'], { cwd: workerPath, stdio: 'ignore' });
      const workerHead = execFileSync('git', ['rev-parse', 'HEAD'], { cwd: workerPath, encoding: 'utf-8' }).trim();

      await writeFile(join(repo, 'shared.txt'), 'same content\n', 'utf-8');
      execFileSync('git', ['add', 'shared.txt'], { cwd: repo, stdio: 'ignore' });
      execFileSync('git', ['commit', '-m', 'leader adds equivalent shared file'], { cwd: repo, stdio: 'ignore' });

      await initTeamState('team-empty-cherry-pick', 'empty cherry-pick test', 'executor', 1, repo);
      const cfg = await readTeamConfig('team-empty-cherry-pick', repo);
      assert.ok(cfg);
      if (!cfg) throw new Error('missing config');
      cfg.leader_pane_id = '';
      cfg.workers[0] = {
        ...cfg.workers[0],
        assigned_tasks: ['1'],
        worktree_repo_root: repo,
        worktree_path: workerPath,
        worktree_branch: 'wk1-empty-pick-branch',
        worktree_detached: false,
        worktree_created: false,
      };
      await saveTeamConfig(cfg, repo);

      await monitorTeam('team-empty-cherry-pick', repo);

      const snapshot = await readMonitorSnapshot('team-empty-cherry-pick', repo);
      assert.notEqual(
        snapshot?.integrationByWorker?.['worker-1']?.status,
        'cherry_pick_conflict',
        'empty cherry-pick should not be reported as conflict',
      );
      assert.equal(
        snapshot?.integrationByWorker?.['worker-1']?.last_integrated_head,
        workerHead,
        'worker head should be recorded as integrated after empty cherry-pick cleanup',
      );

      const leaderMailbox = await listMailboxMessages('team-empty-cherry-pick', 'leader-fixed', repo);
      assert.equal(
        leaderMailbox.some((message) => /CONFLICT AUTO-RESOLVED FAILED: .*cherry-pick/i.test(message.body)),
        false,
        'leader mailbox should not receive conflict noise for empty cherry-picks',
      );

      const events = await readTeamEvents('team-empty-cherry-pick', repo, { wakeableOnly: false });
      assert.equal(
        events.some((event: { type: string }) => event.type === 'worker_cherry_pick_conflict'),
        false,
        'empty cherry-pick should not emit worker_cherry_pick_conflict',
      );
    } finally {
      if (workerPath) {
        await rm(workerPath, { recursive: true, force: true });
      }
      await rm(repo, { recursive: true, force: true });
    }
  });
});
