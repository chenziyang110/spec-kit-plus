import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { describe, it } from 'node:test';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const templateAgents = readFileSync(join(__dirname, '../../../templates/AGENTS.md'), 'utf-8');
const repoAgentsPath = join(__dirname, '../../../AGENTS.md');
const rootAgents = existsSync(repoAgentsPath) ? readFileSync(repoAgentsPath, 'utf-8') : null;

function getAnalyzeRouteRow(content: string): string {
  const row = content
    .split('\n')
    .find((line) => line.includes('analyze') && line.includes('investigate') && line.includes('$analyze'));

  assert.ok(row, 'expected analyze keyword row to exist');
  return row;
}

describe('analyze routing contract', () => {
  it('routes analyze through the analyze skill file in the template AGENTS surface', () => {
    const templateRow = getAnalyzeRouteRow(templateAgents);

    assert.match(templateRow, /\$analyze/i);
    assert.match(templateRow, /read-only deep analysis with ranked synthesis, explicit confidence, and concrete file references/i);
    assert.match(templateAgents, /keyword registry/i);
    assert.match(templateAgents, /analyze.*investigate.*\$analyze/i);
  });

  it('keeps any checked-in root AGENTS surface aligned when present', () => {
    if (rootAgents == null) return;

    const rootRow = getAnalyzeRouteRow(rootAgents);
    assert.match(rootRow, /\$analyze/i);
    assert.match(rootRow, /read-only deep analysis with ranked synthesis, explicit confidence, and concrete file references/i);
  });

  it('does not leave analyze routed through debugger prompts or compatibility aliases', () => {
    const templateRow = getAnalyzeRouteRow(templateAgents);

    assert.doesNotMatch(templateRow, /prompts\/debugger\.md/i);
    assert.doesNotMatch(templateRow, /compatibility alias/i);
    assert.doesNotMatch(templateAgents, /analyze.*prompts\/debugger\.md/i);
    if (rootAgents != null) {
      const rootRow = getAnalyzeRouteRow(rootAgents);
      assert.doesNotMatch(rootRow, /prompts\/debugger\.md/i);
      assert.doesNotMatch(rootRow, /compatibility alias/i);
      assert.doesNotMatch(rootAgents, /analyze.*prompts\/debugger\.md/i);
    }
  });
});
