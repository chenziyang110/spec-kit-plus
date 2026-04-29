import { afterEach, describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  buildWorkerProcessLaunchSpec,
  resolveTeamWorkerCli,
  resolveTeamWorkerCliPlan,
  resolveTeamWorkerLaunchMode,
} from '../tmux-session.js';

const ENV_KEYS = [
  'SPECIFY_TEAM_WORKER_CLI',
  'SPECIFY_TEAM_WORKER_CLI_MAP',
  'SPECIFY_TEAM_WORKER_LAUNCH_MODE',
  'SPECIFY_TEAM_STATE_ROOT',
  'SPECIFY_TEAM_WORKER',
  'SPECIFY_TEAM_LEADER_CLI_PATH',
  'CODEX_HOME',
  'PATH',
  'HTTPS_PROXY',
  'HTTP_PROXY',
  'NO_PROXY',
  'https_proxy',
  'http_proxy',
  'no_proxy',
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

describe('tmux-session specify env contract', () => {
  it('reads SPECIFY_TEAM_WORKER_LAUNCH_MODE', () => {
    assert.equal(
      resolveTeamWorkerLaunchMode({ SPECIFY_TEAM_WORKER_LAUNCH_MODE: 'prompt' }),
      'prompt',
    );
  });

  it('reads SPECIFY_TEAM_WORKER_CLI', () => {
    assert.equal(
      resolveTeamWorkerCli([], { SPECIFY_TEAM_WORKER_CLI: 'gemini' }),
      'gemini',
    );
  });

  it('reads SPECIFY_TEAM_WORKER_CLI_MAP', () => {
    assert.deepEqual(
      resolveTeamWorkerCliPlan(2, [], { SPECIFY_TEAM_WORKER_CLI_MAP: 'codex,claude' }),
      ['codex', 'claude'],
    );
  });

  it('emits SPECIFY_TEAM_* worker env keys in launch specs', () => {
    const stateRoot = '/tmp/workspace/.specify/runtime/state';
    const spec = buildWorkerProcessLaunchSpec(
      'alpha',
      2,
      [],
      '/tmp/workspace',
      { SPECIFY_TEAM_STATE_ROOT: stateRoot },
      'codex',
    );

    assert.equal(spec.env.SPECIFY_TEAM_WORKER, 'alpha/worker-2');
    assert.equal(spec.env.SPECIFY_TEAM_STATE_ROOT, stateRoot);
    assert.equal(typeof spec.env.SPECIFY_TEAM_LEADER_CLI_PATH, 'string');
    assert.equal(spec.env.OMX_TEAM_WORKER, undefined);
    assert.equal(spec.env.OMX_TEAM_STATE_ROOT, undefined);
  });
});
