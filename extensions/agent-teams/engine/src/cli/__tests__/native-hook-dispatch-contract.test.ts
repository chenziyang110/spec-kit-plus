import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { join } from 'node:path';
import { describe, it } from 'node:test';

describe('native hook dispatch contract', () => {
  it('force-enables native hook dispatch in the CLI path', async () => {
    const source = await readFile(join(process.cwd(), 'src', 'cli', 'index.ts'), 'utf-8');
    assert.match(
      source,
      /async function emitNativeHookEvent[\s\S]*?await dispatchHookEvent\(payload,\s*\{\s*cwd,\s*enabled:\s*true,\s*\}\);/,
    );
  });
});
