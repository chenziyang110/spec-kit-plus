import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { sanitizeTmuxAlertText } from '../tmux.js';

describe('sanitizeTmuxAlertText - SP metadata', () => {
  it('drops HUD metadata lines that use the new [SP] label', () => {
    const raw = [
      'fix/issue-1525-post-stop-keyword-replay',
      'fix/issue-1525-post-stop-keyword-replay | ralph:2/50 | turns:4 | session:1m | last:5s ago',
      '[SP#3] ultrawork active',
    ].join('\n');

    assert.equal(sanitizeTmuxAlertText(raw), undefined);
  });
});
