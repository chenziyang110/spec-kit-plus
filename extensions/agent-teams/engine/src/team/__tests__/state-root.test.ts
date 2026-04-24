import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { resolveCanonicalTeamStateRoot } from '../state-root.js';

describe('state-root', () => {
  it('resolveCanonicalTeamStateRoot resolves to leader .omx/state', () => {
    assert.equal(
      resolveCanonicalTeamStateRoot('/tmp/demo/project', {}),
      '/tmp/demo/project/.omx/state',
    );
  });

  it('prefers OMX_TEAM_STATE_ROOT when present', () => {
    assert.equal(
      resolveCanonicalTeamStateRoot('/tmp/demo/project', {
        OMX_TEAM_STATE_ROOT: '/tmp/shared/team-state',
      }),
      '/tmp/shared/team-state',
    );
  });

  it('resolves relative OMX_TEAM_STATE_ROOT from the leader cwd', () => {
    assert.equal(
      resolveCanonicalTeamStateRoot('/tmp/demo/project', {
        OMX_TEAM_STATE_ROOT: '../shared/state',
      }),
      '/tmp/demo/shared/state',
    );
  });
});
