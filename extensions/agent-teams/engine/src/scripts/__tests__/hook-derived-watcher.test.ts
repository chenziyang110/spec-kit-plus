import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import { mkdir, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { describe, it } from 'node:test';

function todaySessionDir(baseHome: string): string {
  const now = new Date();
  return join(
    baseHome,
    '.codex',
    'sessions',
    String(now.getUTCFullYear()),
    String(now.getUTCMonth() + 1).padStart(2, '0'),
    String(now.getUTCDate()).padStart(2, '0'),
  );
}

describe('hook-derived-watcher', () => {
  it('dispatches needs-input for assistant_message content arrays', async () => {
    const base = await mkdtemp(join(tmpdir(), 'omx-hook-derived-array-'));
    const homeDir = join(base, 'home');
    const cwd = join(base, 'cwd');
    const hookLogPath = join(cwd, '.omx', 'hook-events.jsonl');

    try {
      await mkdir(todaySessionDir(homeDir), { recursive: true });
      await mkdir(join(cwd, '.omx', 'hooks'), { recursive: true });

      await writeFile(
        join(cwd, '.omx', 'hooks', 'capture-needs-input.mjs'),
        `import { appendFile, mkdir } from 'node:fs/promises';
import { dirname } from 'node:path';

export async function onHookEvent(event) {
  await mkdir(dirname(${JSON.stringify(hookLogPath)}), { recursive: true });
  await appendFile(${JSON.stringify(hookLogPath)}, JSON.stringify(event) + '\\n');
}
`,
      );

      const rolloutPath = join(todaySessionDir(homeDir), 'rollout-hook-derived-array.jsonl');
      await writeFile(
        rolloutPath,
        [
          JSON.stringify({
            type: 'session_meta',
            payload: {
              id: 'thread-hook-array',
              cwd,
            },
          }),
          JSON.stringify({
            timestamp: new Date().toISOString(),
            type: 'event_msg',
            payload: {
              type: 'assistant_message',
              turn_id: 'turn-hook-array',
              content: [
                {
                  type: 'output_text',
                  text: 'Would you like me to continue with the cleanup?',
                },
                {
                  type: 'output_text',
                  text: 'I need your approval before I keep going.',
                },
              ],
            },
          }),
          '',
        ].join('\n'),
      );

      const watcherScript = new URL('../hook-derived-watcher.js', import.meta.url).pathname;
      const result = spawnSync(
        process.execPath,
        [watcherScript, '--once', '--cwd', cwd, '--poll-ms', '250'],
        {
          cwd,
          env: {
            ...process.env,
            HOME: homeDir,
            OMX_HOOK_DERIVED_SIGNALS: '1',
            OMX_HOOK_PLUGINS: '1',
          },
          encoding: 'utf8',
        },
      );

      assert.equal(result.status, 0, result.stderr || result.stdout);
      assert.equal(existsSync(hookLogPath), true, 'expected needs-input hook log to be written');

      const events = (await readFile(hookLogPath, 'utf-8'))
        .split('\n')
        .map((line) => line.trim())
        .filter(Boolean)
        .map((line) => JSON.parse(line) as Record<string, unknown>);

      assert.equal(events.length, 1);
      assert.equal(events[0].event, 'needs-input');
      assert.equal(events[0].source, 'derived');
      assert.equal(events[0].parser_reason, 'assistant_message_heuristic_question');
      assert.match(String((events[0].context as Record<string, unknown>)?.preview ?? ''), /Would you like me to continue/i);
    } finally {
      await rm(base, { recursive: true, force: true });
    }
  });
});
