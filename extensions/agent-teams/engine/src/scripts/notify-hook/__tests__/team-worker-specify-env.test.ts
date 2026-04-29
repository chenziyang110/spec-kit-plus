import { afterEach, describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  parseTeamWorkerEnv,
  resolveAllWorkersIdleCooldownMs,
  resolveHeartbeatStaleMs,
  resolveStatusStaleMs,
  resolveTeamStateDirForWorker,
  resolveWorkerIdleCooldownMs,
  resolveWorkerIdleNotifyEnabled,
} from '../team-worker.js';

function normalizePath(value: string): string {
  return value.replace(/\\/g, '/').replace(/^[A-Za-z]:/, '');
}

const ENV_KEYS = [
  'SPECIFY_TEAM_STATE_ROOT',
  'SPECIFY_TEAM_LEADER_CWD',
  'SPECIFY_TEAM_WORKER_IDLE_NOTIFY',
  'SPECIFY_TEAM_WORKER_IDLE_COOLDOWN_MS',
  'SPECIFY_TEAM_ALL_IDLE_COOLDOWN_MS',
  'SPECIFY_TEAM_STATUS_STALE_MS',
  'SPECIFY_TEAM_HEARTBEAT_STALE_MS',
  'OMX_TEAM_STATE_ROOT',
  'OMX_TEAM_LEADER_CWD',
  'OMX_TEAM_WORKER_IDLE_NOTIFY',
  'OMX_TEAM_WORKER_IDLE_COOLDOWN_MS',
  'OMX_TEAM_ALL_IDLE_COOLDOWN_MS',
  'OMX_TEAM_STATUS_STALE_MS',
  'OMX_TEAM_HEARTBEAT_STALE_MS',
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

describe('notify-hook team-worker specify env contract', () => {
  it('resolves explicit SPECIFY_TEAM_STATE_ROOT', async () => {
    process.env.SPECIFY_TEAM_STATE_ROOT = '/tmp/shared/.specify/runtime/state';
    const parsed = parseTeamWorkerEnv('alpha/worker-1');
    assert.ok(parsed);
    assert.equal(
      normalizePath(await resolveTeamStateDirForWorker('/tmp/repo', parsed)),
      '/tmp/shared/.specify/runtime/state',
    );
  });

  it('falls back to .specify/runtime/state when no explicit state root exists', async () => {
    const parsed = parseTeamWorkerEnv('alpha/worker-1');
    assert.ok(parsed);
    assert.equal(
      normalizePath(await resolveTeamStateDirForWorker('/tmp/repo', parsed)),
      '/tmp/repo/.specify/runtime/state',
    );
  });

  it('reads SPECIFY_TEAM_* worker timing envs', () => {
    process.env.SPECIFY_TEAM_WORKER_IDLE_NOTIFY = 'off';
    process.env.SPECIFY_TEAM_WORKER_IDLE_COOLDOWN_MS = '45000';
    process.env.SPECIFY_TEAM_ALL_IDLE_COOLDOWN_MS = '90000';
    process.env.SPECIFY_TEAM_STATUS_STALE_MS = '240000';
    process.env.SPECIFY_TEAM_HEARTBEAT_STALE_MS = '300000';

    assert.equal(resolveWorkerIdleNotifyEnabled(), false);
    assert.equal(resolveWorkerIdleCooldownMs(), 45000);
    assert.equal(resolveAllWorkersIdleCooldownMs(), 90000);
    assert.equal(resolveStatusStaleMs(), 240000);
    assert.equal(resolveHeartbeatStaleMs(), 300000);
  });

  it('ignores legacy OMX_TEAM_* worker timing envs after the hard cut', () => {
    process.env.OMX_TEAM_WORKER_IDLE_NOTIFY = 'off';
    process.env.OMX_TEAM_WORKER_IDLE_COOLDOWN_MS = '45000';
    process.env.OMX_TEAM_ALL_IDLE_COOLDOWN_MS = '90000';
    process.env.OMX_TEAM_STATUS_STALE_MS = '240000';
    process.env.OMX_TEAM_HEARTBEAT_STALE_MS = '300000';

    assert.equal(resolveWorkerIdleNotifyEnabled(), true);
    assert.equal(resolveWorkerIdleCooldownMs(), 30000);
    assert.equal(resolveAllWorkersIdleCooldownMs(), 60000);
    assert.equal(resolveStatusStaleMs(), 120000);
    assert.equal(resolveHeartbeatStaleMs(), 180000);
  });
});
