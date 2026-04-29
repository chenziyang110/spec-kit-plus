import { afterEach, describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, rm } from 'node:fs/promises';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { initTeamState, createTask } from '../state.js';

async function loadRuntimeCliModule() {
  process.env.SPECIFY_RUNTIME_CLI_DISABLE_AUTO_START = '1';
  return await import('../runtime-cli.js');
}

const ENV_KEYS = [
  'SPECIFY_RUNTIME_CLI_DISABLE_AUTO_START',
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

describe('runtime-cli specify contract', () => {
  it('reads SPECIFY_TEAM_STATE_ROOT for task result collection', async () => {
    const cwd = await mkdtemp(join(tmpdir(), 'specify-runtime-cli-cwd-'));
    const explicitStateRoot = await mkdtemp(join(tmpdir(), 'specify-runtime-cli-state-'));
    process.env.SPECIFY_TEAM_STATE_ROOT = explicitStateRoot;
    try {
      await initTeamState('env-root-results', 'task', 'executor', 1, cwd);
      await createTask('env-root-results', {
        subject: 'completed task',
        description: 'stored under explicit state root',
        status: 'completed',
        owner: 'worker-1',
        result: 'PASS: explicit root task result',
      }, cwd);

      const runtimeCli = await loadRuntimeCliModule();
      const stateRoot = runtimeCli.resolveRuntimeCliStateRoot(cwd);
      assert.equal(stateRoot, explicitStateRoot);
      assert.deepEqual(runtimeCli.collectTaskResults(stateRoot, 'env-root-results'), [{
        taskId: '1',
        status: 'completed',
        summary: 'PASS: explicit root task result',
      }]);
    } finally {
      await rm(explicitStateRoot, { recursive: true, force: true });
      await rm(cwd, { recursive: true, force: true });
    }
  });

  it('guides operators through sp-teams runtime surfaces', async () => {
    const cwd = await mkdtemp(join(tmpdir(), 'specify-runtime-cli-notice-'));
    try {
      await initTeamState('runtime-cli-preserve-complete', 'task', 'executor', 1, cwd);
      await createTask('runtime-cli-preserve-complete', {
        subject: 'done task',
        description: 'already complete',
        status: 'completed',
        owner: 'worker-1',
        result: 'PASS: complete without shutdown',
      }, cwd);

      const runtimeCli = await loadRuntimeCliModule();
      const result = runtimeCli.buildTerminalCliResult(
        runtimeCli.resolveRuntimeCliStateRoot(cwd),
        'runtime-cli-preserve-complete',
        'complete',
        1,
        Date.now() - 1000,
      );

      assert.match(result.notice, /sp-teams status runtime-cli-preserve-complete --json/);
      assert.match(result.notice, /sp-teams api read-stall-state/);
      assert.match(result.notice, /sp-teams shutdown runtime-cli-preserve-complete/);
      assert.doesNotMatch(result.notice, /sp-team /);
      assert.doesNotMatch(result.notice, /omx team /);
    } finally {
      await rm(cwd, { recursive: true, force: true });
    }
  });
});
