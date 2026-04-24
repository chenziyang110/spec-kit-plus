import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, rm } from 'node:fs/promises';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { hooksCommand } from '../hooks.js';

async function captureHooksCommand(args: string[], env: { OMX_HOOK_PLUGINS?: string }): Promise<string[]> {
  const cwd = await mkdtemp(join(tmpdir(), 'hooks-command-'));
  const originalCwd = process.cwd();
  const originalEnv = process.env.OMX_HOOK_PLUGINS;
  const originalLog = console.log;
  const logs: string[] = [];

  console.log = (...items: unknown[]) => {
    logs.push(items.map(String).join(' '));
  };

  if (env.OMX_HOOK_PLUGINS === undefined) {
    delete process.env.OMX_HOOK_PLUGINS;
  } else {
    process.env.OMX_HOOK_PLUGINS = env.OMX_HOOK_PLUGINS;
  }

  process.chdir(cwd);

  try {
    await hooksCommand(args);
    return logs;
  } finally {
    process.chdir(originalCwd);
    if (originalEnv === undefined) {
      delete process.env.OMX_HOOK_PLUGINS;
    } else {
      process.env.OMX_HOOK_PLUGINS = originalEnv;
    }
    console.log = originalLog;
    await rm(cwd, { recursive: true, force: true });
  }
}

describe('hooksCommand', () => {
  it('reports plugins enabled by default in help output', async () => {
    const logs = await captureHooksCommand(['--help'], {});
    assert.match(logs.join('\n'), /Plugins are enabled by default\. Disable with OMX_HOOK_PLUGINS=0\./);
  });

  it('reports init output with the same enabled-by-default wording', async () => {
    const logs = await captureHooksCommand(['init'], {});
    assert.match(logs.join('\n'), /Plugins are enabled by default\. Disable with OMX_HOOK_PLUGINS=0\./);
  });

  it('reports status as disabled only when OMX_HOOK_PLUGINS=0', async () => {
    const enabledLogs = await captureHooksCommand(['status'], {});
    assert.match(enabledLogs.join('\n'), /Plugins enabled: yes/);

    const disabledLogs = await captureHooksCommand(['status'], { OMX_HOOK_PLUGINS: '0' });
    assert.match(disabledLogs.join('\n'), /Plugins enabled: no \(disabled with OMX_HOOK_PLUGINS=0\)/);
  });
});
