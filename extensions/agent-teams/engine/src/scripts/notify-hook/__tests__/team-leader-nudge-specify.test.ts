import { afterEach, describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import {
  resolveFallbackProgressStallThresholdMs,
  resolveLeaderAllIdleNudgeCooldownMs,
  resolveLeaderNudgeIntervalMs,
  resolveLeaderStalenessThresholdMs,
  resolveWorkerTurnStallThresholdMs,
} from '../team-leader-nudge.js';

const ENV_KEYS = [
  'SPECIFY_TEAM_LEADER_NUDGE_MS',
  'SPECIFY_TEAM_LEADER_ALL_IDLE_COOLDOWN_MS',
  'SPECIFY_TEAM_LEADER_STALE_MS',
  'SPECIFY_TEAM_PROGRESS_STALL_MS',
  'SPECIFY_TEAM_WORKER_TURN_STALL_MS',
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

describe('notify-hook team-leader specify contract', () => {
  it('reads SPECIFY_TEAM_* nudge timing envs', () => {
    process.env.SPECIFY_TEAM_LEADER_NUDGE_MS = '45000';
    process.env.SPECIFY_TEAM_LEADER_ALL_IDLE_COOLDOWN_MS = '55000';
    process.env.SPECIFY_TEAM_LEADER_STALE_MS = '240000';
    process.env.SPECIFY_TEAM_PROGRESS_STALL_MS = '180000';
    process.env.SPECIFY_TEAM_WORKER_TURN_STALL_MS = '45000';

    assert.equal(resolveLeaderNudgeIntervalMs(), 45000);
    assert.equal(resolveLeaderAllIdleNudgeCooldownMs(), 55000);
    assert.equal(resolveLeaderStalenessThresholdMs(), 240000);
    assert.equal(resolveFallbackProgressStallThresholdMs(), 180000);
    assert.equal(resolveWorkerTurnStallThresholdMs(), 45000);
  });

  it('guides operators through sp-teams instead of omx team', () => {
    const content = readFileSync(
      join(process.cwd(), 'extensions', 'agent-teams', 'engine', 'src', 'scripts', 'notify-hook', 'team-leader-nudge.ts'),
      'utf-8',
    );

    assert.match(content, /sp-teams shutdown/);
    assert.match(content, /sp-teams status/);
    assert.doesNotMatch(content, /omx team shutdown/);
    assert.doesNotMatch(content, /omx team status/);
  });
});
