import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

describe('runtime tmux session prefix source contract', () => {
  it('uses specify-team-* across active team runtime sources', () => {
    const runtime = readFileSync(
      join(process.cwd(), 'extensions', 'agent-teams', 'engine', 'src', 'team', 'runtime.ts'),
      'utf-8',
    );
    const state = readFileSync(
      join(process.cwd(), 'extensions', 'agent-teams', 'engine', 'src', 'team', 'state.ts'),
      'utf-8',
    );
    const notificationsTmux = readFileSync(
      join(process.cwd(), 'extensions', 'agent-teams', 'engine', 'src', 'notifications', 'tmux.ts'),
      'utf-8',
    );

    assert.match(runtime, /specify-team-\$\{teamName\}/);
    assert.match(runtime, /specify-team-\$\{sanitized\}/);
    assert.match(state, /specify-team-\$\{teamName\}/);
    assert.match(notificationsTmux, /specify-team-\$\{sanitized\}/);
    assert.doesNotMatch(runtime, /omx-team-\$\{teamName\}/);
    assert.doesNotMatch(runtime, /omx-team-\$\{sanitized\}/);
    assert.doesNotMatch(state, /omx-team-\$\{teamName\}/);
    assert.doesNotMatch(notificationsTmux, /omx-team-\$\{sanitized\}/);
  });
});
