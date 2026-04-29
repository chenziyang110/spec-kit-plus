import { afterEach, describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';
import { chmod, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { delimiter, join } from 'node:path';
import { tmpdir } from 'node:os';
import { dismissTrustPromptIfPresent, waitForWorkerReady } from '../tmux-session.js';

const CLAUDE_BYPASS_PROMPT_CAPTURE = `Bypass Permissions mode

1. No, exit
2. Yes, I accept

Press Enter to confirm`;

async function withMockTmuxFixture<T>(
  dirPrefix: string,
  tmuxScript: (tmuxLogPath: string, acceptedFile: string) => string,
  run: (ctx: { logPath: string; acceptedFile: string }) => Promise<T>,
): Promise<T> {
  const fakeBinDir = await mkdtemp(join(tmpdir(), dirPrefix));
  const logPath = join(fakeBinDir, 'tmux.log');
  const acceptedFile = join(fakeBinDir, 'accepted.flag');
  const tmuxStubPath = join(fakeBinDir, 'tmux.cmd');
  const previousPath = process.env.PATH;

  try {
    await writeFile(tmuxStubPath, tmuxScript(logPath, acceptedFile));
    await chmod(tmuxStubPath, 0o755);
    process.env.PATH = `${fakeBinDir}${delimiter}${previousPath ?? ''}`;
    return await run({ logPath, acceptedFile });
  } finally {
    if (typeof previousPath === 'string') process.env.PATH = previousPath;
    else delete process.env.PATH;
    await rm(fakeBinDir, { recursive: true, force: true });
  }
}

const ENV_KEYS = [
  'SPECIFY_TEAM_AUTO_TRUST',
  'OMX_TEAM_AUTO_TRUST',
  'SPECIFY_TEAM_AUTO_ACCEPT_BYPASS',
  'OMX_TEAM_AUTO_ACCEPT_BYPASS',
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

describe('tmux-session specify control envs', () => {
  it('disables trust auto-dismiss when SPECIFY_TEAM_AUTO_TRUST=0', async () => {
    process.env.SPECIFY_TEAM_AUTO_TRUST = '0';
    await withMockTmuxFixture(
      'specify-dismiss-trust-disabled-',
      (logPath) => `@echo off
echo %*>> "${logPath}"
exit /b 0
`,
      async ({ logPath }) => {
        assert.equal(dismissTrustPromptIfPresent('specify-team-x', 1), false);
        assert.equal(existsSync(logPath), false);
      },
    );
  });

  it('disables Claude bypass auto-accept when SPECIFY_TEAM_AUTO_ACCEPT_BYPASS=0', async () => {
    process.env.SPECIFY_TEAM_AUTO_ACCEPT_BYPASS = '0';
    await withMockTmuxFixture(
      'specify-bypass-disabled-',
      (logPath) => `@echo off
echo %*>> "${logPath}"
if "%1"=="capture-pane" (
  echo Bypass Permissions mode
  echo.
  echo 1. No, exit
  echo 2. Yes, I accept
  echo.
  echo Press Enter to confirm
)
exit /b 0
`,
      async ({ logPath }) => {
        assert.equal(waitForWorkerReady('specify-team-x', 1, 250), false);
        const log = existsSync(logPath) ? await readFile(logPath, 'utf-8') : '';
        assert.doesNotMatch(log, /send-keys/);
      },
    );
  });

});
