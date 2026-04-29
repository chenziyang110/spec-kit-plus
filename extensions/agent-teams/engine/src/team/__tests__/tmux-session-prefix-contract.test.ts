import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { initTeamState, readTeamConfig } from '../state.js';

describe('team tmux session prefix contract', () => {
  it('initTeamState defaults tmux_session to specify-team-*', async () => {
    const cwd = mkdtempSync(join(tmpdir(), 'specify-team-prefix-state-'));
    try {
      await initTeamState('team-1', 'do stuff', 'executor', 2, cwd);
      const config = await readTeamConfig('team-1', cwd);
      assert.equal(config?.tmux_session, 'specify-team-team-1');
    } finally {
      rmSync(cwd, { recursive: true, force: true });
    }
  });
});
