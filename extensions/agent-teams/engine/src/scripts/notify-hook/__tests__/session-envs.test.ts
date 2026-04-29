import { afterEach, describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { mkdir, mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { resolveInvocationSessionId } from '../managed-tmux.js';
import { readCurrentSessionId } from '../state-io.js';

const ENV_KEYS = ['SPECIFY_SESSION_ID', 'OMX_SESSION_ID', 'CODEX_SESSION_ID', 'SESSION_ID'] as const;
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

describe('notify-hook session env contract', () => {
  it('prefers SPECIFY_SESSION_ID when resolving current session state scope', async () => {
    const cwd = await mkdtemp(join(tmpdir(), 'specify-session-env-'));
    try {
      const stateDir = join(cwd, '.specify', 'runtime', 'state');
      const sessionId = 'sess-specify';
      await mkdir(join(stateDir, 'sessions', sessionId), { recursive: true });
      process.env.SPECIFY_SESSION_ID = sessionId;

      assert.equal(await readCurrentSessionId(stateDir), sessionId);
    } finally {
      await rm(cwd, { recursive: true, force: true });
    }
  });

  it('prefers SPECIFY_SESSION_ID when resolving invocation session ids', () => {
    process.env.SPECIFY_SESSION_ID = 'sess-specify';
    delete process.env.OMX_SESSION_ID;
    delete process.env.CODEX_SESSION_ID;
    delete process.env.SESSION_ID;

    assert.equal(resolveInvocationSessionId({}), 'sess-specify');
  });
});
