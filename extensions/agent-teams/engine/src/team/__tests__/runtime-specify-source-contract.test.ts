import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

describe('team runtime specify source contract', () => {
  it('uses SPECIFY_* startup envs and sp-teams operator guidance', () => {
    const content = readFileSync(
      join(process.cwd(), 'extensions', 'agent-teams', 'engine', 'src', 'team', 'runtime.ts'),
      'utf-8',
    );

    assert.match(content, /SPECIFY_TEAM_STATE_ROOT/);
    assert.match(content, /SPECIFY_TEAM_LEADER_CWD/);
    assert.match(content, /SPECIFY_TEAM_READY_TIMEOUT_MS/);
    assert.match(content, /SPECIFY_TEAM_STARTUP_EVIDENCE_TIMEOUT_MS/);
    assert.match(content, /SPECIFY_TEAM_STARTUP_DISPATCH_RETRIES/);
    assert.match(content, /SPECIFY_TEAM_STARTUP_DISPATCH_RETRY_DELAY_MS/);
    assert.match(content, /SPECIFY_TEAM_SKIP_READY_WAIT/);
    assert.match(content, /SPECIFY_TEAM_SKIP_STARTUP_EVIDENCE/);
    assert.match(content, /SPECIFY_TEAM_WORKER_LAUNCH_ARGS/);
    assert.match(content, /SPECIFY_TEAM_WORKER_CLI_MAP/);
    assert.match(content, /SPECIFY_TEAM_WORKER_CLI/);
    assert.match(content, /SPECIFY_TEAM_DISPLAY_MODE/);
    assert.match(content, /SPECIFY_TEAM_WORKER_LAUNCH_MODE/);
    assert.match(content, /SPECIFY_TEAM_WORKTREE_PATH/);
    assert.match(content, /SPECIFY_TEAM_WORKTREE_BRANCH/);
    assert.match(content, /SPECIFY_TEAM_WORKTREE_DETACHED/);
    assert.match(content, /SPECIFY_SESSION_ID/);
    assert.match(content, /sp-teams status/);
    assert.match(content, /sp-teams resume/);
    assert.match(content, /sp-teams shutdown/);
    assert.doesNotMatch(content, /omx team status/);
    assert.doesNotMatch(content, /omx team resume/);
    assert.doesNotMatch(content, /omx team shutdown/);
  });

  it('uses SPECIFY_* control envs in tmux-session', () => {
    const content = readFileSync(
      join(process.cwd(), 'extensions', 'agent-teams', 'engine', 'src', 'team', 'tmux-session.ts'),
      'utf-8',
    );

    assert.match(content, /SPECIFY_TEAM_AUTO_INTERRUPT_RETRY/);
    assert.match(content, /SPECIFY_TEAM_MOUSE/);
    assert.match(content, /SPECIFY_TEAM_AUTO_ACCEPT_BYPASS/);
    assert.match(content, /SPECIFY_TEAM_SEND_STRATEGY/);
    assert.match(content, /SPECIFY_TEAM_AUTO_TRUST/);
    assert.match(content, /SPECIFY_TEAM_STRICT_SUBMIT/);
    assert.doesNotMatch(content, /OMX_TEAM_AUTO_INTERRUPT_RETRY/);
    assert.doesNotMatch(content, /OMX_TEAM_MOUSE/);
    assert.doesNotMatch(content, /OMX_TEAM_AUTO_ACCEPT_BYPASS/);
    assert.doesNotMatch(content, /OMX_TEAM_SEND_STRATEGY/);
    assert.doesNotMatch(content, /OMX_TEAM_AUTO_TRUST/);
    assert.doesNotMatch(content, /OMX_TEAM_STRICT_SUBMIT/);
  });
});
