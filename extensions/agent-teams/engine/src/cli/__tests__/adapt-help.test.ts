import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, rm } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { tmpdir } from 'node:os';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

function runOmx(cwd: string, argv: string[]) {
  const testDir = dirname(fileURLToPath(import.meta.url));
  const repoRoot = join(testDir, '..', '..', '..');
  const omxBin = join(repoRoot, 'dist', 'cli', 'omx.js');
  return spawnSync(process.execPath, [omxBin, ...argv], {
    cwd,
    encoding: 'utf-8',
    env: {
      ...process.env,
      OMX_AUTO_UPDATE: '0',
      OMX_NOTIFY_FALLBACK: '0',
      OMX_HOOK_DERIVED_SIGNALS: '0',
    },
  });
}

describe('omx adapt help', () => {
  it('documents adapt in top-level help and routes adapt-local help output', async () => {
    const cwd = await mkdtemp(join(tmpdir(), 'omx-adapt-help-'));
    try {
      const mainHelp = runOmx(cwd, ['--help']);
      assert.equal(mainHelp.status, 0, mainHelp.stderr || mainHelp.stdout);
      assert.match(mainHelp.stdout, /omx adapt\s+Scaffold OMX-owned adapter foundations for persistent external targets/i);

      const adaptHelp = runOmx(cwd, ['adapt', '--help']);
      assert.equal(adaptHelp.status, 0, adaptHelp.stderr || adaptHelp.stdout);
      assert.match(adaptHelp.stdout, /Usage: omx adapt <target> <probe\|status\|init\|envelope\|doctor>/i);
    } finally {
      await rm(cwd, { recursive: true, force: true });
    }
  });
});
