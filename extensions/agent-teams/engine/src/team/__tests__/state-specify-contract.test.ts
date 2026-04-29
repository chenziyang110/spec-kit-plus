import { afterEach, describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, rm } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { initTeamState, readTeamConfig, readTeamManifestV2 } from '../state.js';

const ENV_KEYS = [
  'SPECIFY_TEAM_DISPLAY_MODE',
  'SPECIFY_TEAM_WORKER_LAUNCH_MODE',
  'SPECIFY_SESSION_ID',
  'SPECIFY_TEAM_WORKER',
  'SPECIFY_TEAM_STATE_ROOT',
] as const;

const ORIGINAL_ENV = new Map<string, string | undefined>(
  ENV_KEYS.map((key) => [key, process.env[key]]),
);

afterEach(() => {
  for (const key of ENV_KEYS) {
    const original = ORIGINAL_ENV.get(key);
    if (typeof original === 'string') process.env[key] = original;
    else delete process.env[key];
  }
});

describe('state specify contract', () => {
  it('initializes policy and leader metadata from SPECIFY_* env', async () => {
    const cwd = await mkdtemp(join(tmpdir(), 'specify-state-contract-'));
    try {
      process.env.SPECIFY_TEAM_DISPLAY_MODE = 'tmux';
      process.env.SPECIFY_TEAM_WORKER_LAUNCH_MODE = 'prompt';
      process.env.SPECIFY_SESSION_ID = 'session-xyz';
      process.env.SPECIFY_TEAM_WORKER = 'leader-fixed';
      process.env.SPECIFY_TEAM_STATE_ROOT = join(cwd, '.specify', 'runtime', 'state');

      await initTeamState('team-specify-env', 'task', 'executor', 2, cwd);
      const config = await readTeamConfig('team-specify-env', cwd);
      const manifest = await readTeamManifestV2('team-specify-env', cwd);

      assert.equal(config?.worker_launch_mode, 'prompt');
      assert.equal(manifest?.leader.session_id, 'session-xyz');
      assert.equal(manifest?.leader.worker_id, 'leader-fixed');
      assert.equal(manifest?.policy.display_mode, 'split_pane');
      assert.equal(manifest?.policy.worker_launch_mode, 'prompt');
      assert.equal(
        existsSync(join(cwd, '.specify', 'runtime', 'state', 'team', 'team-specify-env', 'config.json')),
        true,
      );
      assert.equal(
        existsSync(join(cwd, '.specify', 'runtime', 'state', 'team', 'team-specify-env', 'manifest.v2.json')),
        true,
      );
    } finally {
      await rm(cwd, { recursive: true, force: true });
    }
  });
});
