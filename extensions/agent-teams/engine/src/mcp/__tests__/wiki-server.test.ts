import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { join } from 'node:path';

const REQUIRED_TOOLS = [
  'wiki_ingest',
  'wiki_query',
  'wiki_lint',
  'wiki_add',
  'wiki_list',
  'wiki_read',
  'wiki_delete',
  'wiki_refresh',
] as const;

describe('mcp/wiki-server module contract', () => {
  it('declares the expected wiki MCP tools', async () => {
    const src = await readFile(join(process.cwd(), 'src/mcp/wiki-server.ts'), 'utf8');
    const toolNames = Array.from(src.matchAll(/name:\s*'([^']+)'/g)).map((match) => match[1]);

    for (const tool of REQUIRED_TOOLS) {
      assert.ok(toolNames.includes(tool), `missing tool declaration: ${tool}`);
    }
  });

  it('delegates wiki stdio lifecycle bootstrapping to the shared helper', async () => {
    const src = await readFile(join(process.cwd(), 'src/mcp/wiki-server.ts'), 'utf8');

    assert.match(src, /autoStartStdioMcpServer\('wiki', server\)/);
    assert.doesNotMatch(src, /new StdioServerTransport\(\)/);
    assert.doesNotMatch(src, /server\.connect\(transport\)\.catch\(console\.error\);/);
  });
});
