import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { resolveCanonicalTeamStateRoot } from '../state-root.js';

function normalizeSlashes(value: string): string {
  return value.replace(/\\/g, '/');
}

function trimWindowsDrivePrefix(value: string): string {
  return normalizeSlashes(value).replace(/^[A-Za-z]:/, '');
}

describe('state-root', () => {
  it('resolveCanonicalTeamStateRoot resolves to leader .specify/runtime/state', () => {
    assert.equal(
      trimWindowsDrivePrefix(resolveCanonicalTeamStateRoot('/tmp/demo/project', {})),
      '/tmp/demo/project/.specify/runtime/state',
    );
  });

  it('prefers SPECIFY_TEAM_STATE_ROOT when present', () => {
    assert.equal(
      trimWindowsDrivePrefix(resolveCanonicalTeamStateRoot('/tmp/demo/project', {
        SPECIFY_TEAM_STATE_ROOT: '/tmp/shared/team-state',
      })),
      '/tmp/shared/team-state',
    );
  });

  it('resolves relative SPECIFY_TEAM_STATE_ROOT from the leader cwd', () => {
    assert.equal(
      trimWindowsDrivePrefix(resolveCanonicalTeamStateRoot('/tmp/demo/project', {
        SPECIFY_TEAM_STATE_ROOT: '../shared/state',
      })),
      '/tmp/demo/shared/state',
    );
  });
});
