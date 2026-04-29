import { afterEach, describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, rm, readFile, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { initTeamState, createTask } from '../state.js';
import { buildLegacyTeamDeprecationHint, executeTeamApiOperation } from '../api-interop.js';

const ENV_KEYS = ['SPECIFY_TEAM_STATE_ROOT', 'SPECIFY_TEAM_WORKER'] as const;
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

describe('api-interop specify contract', () => {
  it('builds deprecation hints around sp-teams api', () => {
    const hint = buildLegacyTeamDeprecationHint('team_send_message', { team_name: 'alpha' });
    assert.match(hint, /sp-teams api send-message/);
    assert.doesNotMatch(hint, /sp-team /);
    assert.doesNotMatch(hint, /omx team /);
  });

  it('prefers SPECIFY_TEAM_STATE_ROOT over manifest metadata when resolving the team working directory', async () => {
    const teamName = 'list-tsk-env-root';
    const cwdA = await mkdtemp(join(tmpdir(), 'specify-interop-env-a-'));
    const cwdB = await mkdtemp(join(tmpdir(), 'specify-interop-env-b-'));
    process.env.SPECIFY_TEAM_WORKER = `${teamName}/worker-1`;
    try {
      await initTeamState(teamName, 'env root precedence', 'executor', 2, cwdA);
      await initTeamState(teamName, 'env root precedence', 'executor', 2, cwdB);
      await createTask(teamName, { subject: 'From env root', description: 'A lane', status: 'pending' }, cwdA);
      await createTask(teamName, { subject: 'From manifest root', description: 'B lane', status: 'pending' }, cwdB);

      const teamRootA = join(cwdA, '.specify', 'runtime', 'state', 'team', teamName);
      const manifestPath = join(teamRootA, 'manifest.v2.json');
      const manifest = JSON.parse(await readFile(manifestPath, 'utf-8')) as Record<string, unknown>;
      manifest.team_state_root = join(cwdB, '.specify', 'runtime', 'state');
      await writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`, 'utf8');

      process.env.SPECIFY_TEAM_STATE_ROOT = join(cwdA, '.specify', 'runtime', 'state');

      const result = await executeTeamApiOperation('list-tasks', { team_name: teamName }, cwdB);
      assert.equal(result.ok, true);
      if (!result.ok) throw new Error('expected list-tasks to succeed');
      assert.equal(result.data.count, 1);
      const tasks = result.data.tasks as Array<{ subject?: string }>;
      assert.equal(tasks[0]?.subject, 'From env root');
    } finally {
      await rm(cwdA, { recursive: true, force: true });
      await rm(cwdB, { recursive: true, force: true });
    }
  });
});
