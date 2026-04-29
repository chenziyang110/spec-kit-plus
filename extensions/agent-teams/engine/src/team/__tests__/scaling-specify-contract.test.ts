import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { isScalingEnabled } from '../scaling.js';

describe('scaling specify contract', () => {
  it('reads SPECIFY_TEAM_SCALING_ENABLED', () => {
    assert.equal(isScalingEnabled({ SPECIFY_TEAM_SCALING_ENABLED: '1' }), true);
    assert.equal(isScalingEnabled({ SPECIFY_TEAM_SCALING_ENABLED: 'true' }), true);
    assert.equal(isScalingEnabled({ SPECIFY_TEAM_SCALING_ENABLED: '0' }), false);
  });

  it('ignores legacy OMX_TEAM_SCALING_ENABLED after the hard cut', () => {
    assert.equal(isScalingEnabled({ OMX_TEAM_SCALING_ENABLED: '1' }), false);
  });
});
